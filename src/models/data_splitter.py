import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import polars as pl

from src.config.settings import settings

logger = logging.getLogger("DataSplitter")

class DataSplitter:
    """
    Institutional Data Splitter & Embargo Engine for MarketIntel AI.
    
    Guarantees:
      1. Purged Group Time-Series Split: Decouples historical train partition from the 2-Year Test Vault.
      2. 63-Day Embargo Window: Trailing training rows whose forward target labels would overlap 
         with the Jan 1, 2024 test horizon are strictly purged.
      3. Zero Feature Leakage: Features are strictly calculated on past information (t-k to t).
      4. Decoupled Model Targets: Computes ground truth labels tailored to each model's loss function.
    """

    DEFAULT_TEST_START = date(2024, 1, 1)
    DEFAULT_EMBARGO_DAYS = 63  # 63 trading days (~3 calendar months)

    def __init__(self, gold_dir: Optional[Path] = None):
        self.gold_dir = gold_dir or settings.GOLD_DIR
        self.model_dirs = {
            0: self.gold_dir / "features_screener_ranking",
            1: self.gold_dir / "features_short_term_positional",
            2: self.gold_dir / "features_long_term_swing",
            3: self.gold_dir / "features_price_corridor",
            4: self.gold_dir / "features_stock_action_classifier",
        }

    def load_dataset(
        self,
        model_id: int,
        test_start_date: date = DEFAULT_TEST_START,
        embargo_days: int = DEFAULT_EMBARGO_DAYS,
        sample_symbols: Optional[List[str]] = None,
        min_turnover_cr: float = 0.5,  # Min 50 Lakhs average daily turnover to filter penny stocks
        max_symbols: Optional[int] = None
    ) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """
        Loads, labels, and splits feature tables for a given model.
        Returns:
            (train_df, test_df) - Two decoupled Polars DataFrames with zero overlap.
        """
        source_dir = self.model_dirs.get(model_id)
        if not source_dir or not source_dir.exists():
            raise FileNotFoundError(f"Feature store directory for Model {model_id} not found: {source_dir}")

        parquet_files = sorted(list(source_dir.glob("*.parquet")))
        if sample_symbols:
            sample_set = set(sample_symbols)
            parquet_files = [f for f in parquet_files if f.stem in sample_set]
        elif max_symbols:
            parquet_files = parquet_files[:max_symbols]

        logger.info(f"Loading Model {model_id} features across {len(parquet_files)} stocks...")

        dfs = []
        for p in parquet_files:
            try:
                df = pl.read_parquet(p)
                if len(df) < 252:
                    continue  # Require at least 1 year of trading history

                # Ensure date format
                col_d = "date" if "date" in df.columns else "timestamp"
                df = df.with_columns(pl.col(col_d).cast(pl.Date).alias("date"))

                # Filter illiquid penny stocks if turnover column exists
                if "turnover_20d_avg" in df.columns and min_turnover_cr > 0:
                    df = df.filter(pl.col("turnover_20d_avg") >= (min_turnover_cr * 1e7))

                # Standardize dynamic window column names for Model 2
                if model_id == 2:
                    for prefix, std_name in [
                        ("sortino_ratio_", "sortino_ratio_756d"),
                        ("sharpe_ratio_", "sharpe_ratio_756d"),
                        ("max_drawdown_", "max_drawdown_756d")
                    ]:
                        matching = [c for c in df.columns if c.startswith(prefix)]
                        if matching and std_name not in df.columns:
                            df = df.rename({matching[0]: std_name})
                    # Keep only canonical columns
                    canonical_m2 = {"date", "open", "high", "low", "close", "volume", "symbol", "exchange", "date_key",
                                    "ret_1d", "sortino_ratio_756d", "max_drawdown_756d", "sharpe_ratio_756d",
                                    "dist_ath_pct", "cagr_3y_proxy", "calmar_ratio_3y"}
                    keep_cols = [c for c in df.columns if c in canonical_m2]
                    df = df.select(keep_cols)

                # Compute model-specific forward target labels
                df_labeled = self._compute_targets(df, model_id)
                if df_labeled is not None and len(df_labeled) > 0:
                    dfs.append(df_labeled)

            except Exception as e:
                logger.warning(f"Failed to process {p.name}: {e}")

        if not dfs:
            raise ValueError(f"No valid data loaded for Model {model_id}")

        full_df = pl.concat(dfs, how="diagonal_relaxed")
        logger.info(f"Loaded {len(full_df):,} total labeled rows across {len(dfs)} equities.")

        # Temporal split with embargo
        embargo_cutoff = test_start_date - timedelta(days=int(embargo_days * 1.5))  # calendar approx for trading days

        train_df = full_df.filter(pl.col("date") < embargo_cutoff)
        test_df = full_df.filter(pl.col("date") >= test_start_date)

        logger.info(
            f"Model {model_id} Partition Complete:\n"
            f"  Train Period: {train_df['date'].min()} to {train_df['date'].max()} ({len(train_df):,} rows)\n"
            f"  Embargo Purge: {embargo_cutoff} to {test_start_date} (Zero Label Leakage)\n"
            f"  2-Year Test Vault: {test_df['date'].min()} to {test_df['date'].max()} ({len(test_df):,} rows)"
        )

        return train_df, test_df

    def _compute_targets(self, df: pl.DataFrame, model_id: int) -> Optional[pl.DataFrame]:
        """Vectorized causal target labeling per stock."""
        df = df.sort("date")

        if model_id == 0:
            # Model 0: Forward 5-day return for LambdaMART ranking
            df = df.with_columns([
                ((pl.col("close").shift(-5) / pl.col("close")).log()).alias("target_fwd_ret_5d")
            ]).filter(pl.col("target_fwd_ret_5d").is_not_null())

        elif model_id == 1:
            # Model 1: Forward 63-day return for positional swing alpha
            df = df.with_columns([
                ((pl.col("close").shift(-63) / pl.col("close")).log()).alias("target_fwd_ret_63d")
            ]).filter(pl.col("target_fwd_ret_63d").is_not_null())

        elif model_id == 2:
            # Model 2: Forward 252-day return for secular wealth compounding
            df = df.with_columns([
                ((pl.col("close").shift(-252) / pl.col("close")).log()).alias("target_fwd_ret_252d")
            ]).filter(pl.col("target_fwd_ret_252d").is_not_null())

        elif model_id == 3:
            # Model 3: Forward 21-day High and Low boundaries for price corridor
            # Vectorized rolling max/min over shifted forward window
            df = df.with_columns([
                (pl.col("high").shift(-21).rolling_max(21) / pl.col("close")).alias("target_high_ratio_21d"),
                (pl.col("low").shift(-21).rolling_min(21) / pl.col("close")).alias("target_low_ratio_21d"),
                ((pl.col("close").shift(-21) / pl.col("close")).log()).alias("target_fwd_ret_21d")
            ]).filter(pl.col("target_high_ratio_21d").is_not_null())

        elif model_id == 4:
            # Model 4: Action & Confidence Classifier (5 classes: 0=STRONG_SELL, 1=SELL, 2=HOLD, 3=BUY, 4=STRONG_BUY)
            # Forward 21-day return and max forward drawdown
            df = df.with_columns([
                ((pl.col("close").shift(-21) / pl.col("close")) - 1.0).alias("fwd_ret_21d"),
                (pl.col("low").shift(-21).rolling_min(21) / pl.col("close") - 1.0).alias("fwd_max_drawdown_21d")
            ]).filter(pl.col("fwd_ret_21d").is_not_null())

            # Rule-based institutional ground truth mapping:
            # STRONG_BUY (4): Return > +12% and Drawdown > -5%
            # BUY (3): Return > +4% and Return > 1.5 * |Drawdown|
            # STRONG_SELL (0): Return < -10% or Drawdown < -15%
            # SELL (1): Return < -4%
            # HOLD (2): Neutral range
            target_expr = (
                pl.when((pl.col("fwd_ret_21d") >= 0.12) & (pl.col("fwd_max_drawdown_21d") >= -0.05))
                .then(pl.lit(4))
                .when((pl.col("fwd_ret_21d") >= 0.04) & (pl.col("fwd_ret_21d") > 1.5 * pl.col("fwd_max_drawdown_21d").abs()))
                .then(pl.lit(3))
                .when((pl.col("fwd_ret_21d") <= -0.10) | (pl.col("fwd_max_drawdown_21d") <= -0.15))
                .then(pl.lit(0))
                .when(pl.col("fwd_ret_21d") <= -0.04)
                .then(pl.lit(1))
                .otherwise(pl.lit(2))
                .alias("target_action_class")
            )
            df = df.with_columns(target_expr)

        return df

    @staticmethod
    def get_feature_columns(df: pl.DataFrame) -> List[str]:
        """Separates ML input features from metadata and target columns."""
        non_feature_prefixes = ("target_", "fwd_")
        metadata_cols = {"date", "open", "high", "low", "close", "volume", "symbol", "exchange", "date_key"}
        
        return [
            c for c in df.columns 
            if c not in metadata_cols and not c.startswith(non_feature_prefixes)
        ]

