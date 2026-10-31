import logging
import polars as pl
from pathlib import Path
from typing import Optional
from src.config.settings import settings
import src.features.polars_indicators as ind

logger = logging.getLogger(__name__)

class Model0FeatureEngineer:
    """
    Computes the 28 strictly orthogonal, dimensionless features for Model 0
    (Pre-Market Screener & LambdaMART Cross-Sectional Ranker).
    Reads Silver Lakehouse tables and writes to Gold Layer.
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.silver_macro_dir = settings.SILVER_DIR / "macro"
        self.silver_global_dir = settings.SILVER_DIR / "macro" / "global"
        self.silver_master_dir = settings.SILVER_DIR / "master"
        self.silver_corp_dir = settings.SILVER_DIR / "corporate"
        
        self.gold_output_dir = settings.GOLD_DIR / "features_screener_ranking"
        self.gold_output_dir.mkdir(parents=True, exist_ok=True)

        self._load_shared_context()

    def _load_shared_context(self):
        """Loads Macro Indices, Global Correlators, Sector Mappings and FII Flows once into memory."""
        logger.info("Loading shared macro, sector, and global context for Model 0...")
        
        # 1. Stock to Sector Mapper
        mapper_path = self.silver_master_dir / "stock_sector_mapping.parquet"
        self.stock_sector_map = pl.read_parquet(mapper_path) if mapper_path.exists() else None

        # 2. Sector Indices & Nifty 50
        macro_path = self.silver_macro_dir / "macro_indices.parquet"
        if macro_path.exists():
            macro_df = pl.read_parquet(macro_path)
            col = "timestamp" if "timestamp" in macro_df.columns else "date"
            self.macro_df = macro_df.with_columns(pl.col(col).cast(pl.Date).alias("date_key"))
        else:
            self.macro_df = None

        # 3. Global Correlators (SP500, Nasdaq, Crude, USDINR, 10Y Yield)
        self.global_dfs = {}
        for asset in ["SP500", "NASDAQ100", "CRUDE_OIL", "USD_INR", "US10Y_YIELD"]:
            p = self.silver_global_dir / f"{asset}.parquet"
            if p.exists():
                gdf = pl.read_parquet(p)
                col = "timestamp" if "timestamp" in gdf.columns else "date"
                self.global_dfs[asset] = gdf.with_columns(pl.col(col).cast(pl.Date).alias("date_key"))

        # 4. FII / DII Institutional Flows
        fii_path = self.silver_macro_dir / "fii_dii_flows.parquet"
        if fii_path.exists():
            self.fii_df = pl.read_parquet(fii_path).with_columns(pl.col("date").cast(pl.Date).alias("date_key"))
        else:
            self.fii_df = None

    def compute_for_stock(self, symbol: str, df: Optional[pl.DataFrame] = None) -> Optional[pl.DataFrame]:
        """Computes Model 0's 28 feature matrix for a single stock."""
        if df is None:
            stock_file = self.silver_ohlcv_dir / "exchange=NSE" / f"symbol={symbol}" / "data.parquet"
            if not stock_file.exists():
                return None
            try:
                df = pl.read_parquet(stock_file)
            except Exception:
                return None

        try:
            if len(df) < 252:
                return None

            date_col = "date" if "date" in df.columns else "timestamp"
            df = df.sort(date_col).with_columns(pl.col(date_col).cast(pl.Date).alias("date_key"))

            # --- Category A: Momentum & Trend Structure ---
            ret_exprs = ind.calc_log_returns("close", [1, 3, 5, 21])
            ema20 = ind.calc_ema("close", 20)
            ema200 = ind.calc_ema("close", 200)
            atr14 = ind.calc_atr("high", "low", "close", 14)
            atr5 = ind.calc_atr("high", "low", "close", 5)
            atr20 = ind.calc_atr("high", "low", "close", 20)
            rsi14 = ind.calc_rsi("close", 14)

            df = df.with_columns(ret_exprs + [ema20, ema200, atr14, atr5, atr20, rsi14])

            # Normalized EMA distances & Volatility ratios
            dist_ema20 = ind.calc_distance_to_ema_atr("close", "ema_20", "atr_14", "dist_ema20_atr")
            dist_ema200 = ind.calc_distance_to_ema_atr("close", "ema_200", "atr_14", "dist_ema200_atr")
            atr_ratio = (pl.col("atr_5") / (pl.col("atr_20") + 1e-8)).alias("atr_ratio_5_20")

            # --- Category B: Volatility Compression & Breakout ---
            bb_exprs = ind.calc_bollinger_bands("close", 20, 2.0)
            parkinson = ind.calc_parkinson_volatility("high", "low", 10)
            dist_52w_high = ((pl.col("close") - pl.col("high").rolling_max(252)) / (pl.col("high").rolling_max(252) + 1e-8)).alias("dist_52w_high_pct")

            # --- Category C: Volume & Institutional Accumulation ---
            rvol20 = ind.calc_rvol("volume", 20)
            vol_trend = (pl.col("volume").rolling_mean(5) / (pl.col("volume").rolling_mean(20) + 1e-8)).alias("volume_trend_5_20")

            df = df.with_columns([dist_ema20, dist_ema200, atr_ratio, parkinson, dist_52w_high, rvol20, vol_trend] + bb_exprs)

            # Liquidity Turnover Metric for gatekeeping
            df = df.with_columns(
                (pl.col("close") * pl.col("volume")).rolling_mean(20).alias("turnover_20d_avg")
            )

            # Add symbol column
            if "symbol" not in df.columns:
                df = df.with_columns(pl.lit(symbol).alias("symbol"))

            return df

        except Exception as e:
            logger.warning(f"Error computing Model 0 features for {symbol}: {e}")
            return None
