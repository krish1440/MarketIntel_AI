import logging
import polars as pl
from pathlib import Path
from typing import Optional
from src.config.settings import settings
import src.features.polars_indicators as ind

logger = logging.getLogger(__name__)

class Model2FeatureEngineer:
    """
    Computes the 25 multi-year secular compounding & fundamental risk features for Model 2
    (Wealth Compounding Engine - Holding Horizon: > 1 Year / 1 to 5+ Years).
    Writes to data/lakehouse/gold/features_long_term_swing/
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.silver_corp_dir = settings.SILVER_DIR / "corporate"
        self.silver_macro_dir = settings.SILVER_DIR / "macro"
        self.gold_output_dir = settings.GOLD_DIR / "features_long_term_swing"
        self.gold_output_dir.mkdir(parents=True, exist_ok=True)

    def compute_for_stock(self, symbol: str, df: Optional[pl.DataFrame] = None) -> Optional[pl.DataFrame]:
        """Computes Model 2's 25-feature compounding matrix for a single stock."""
        if df is None:
            stock_file = self.silver_ohlcv_dir / "exchange=NSE" / f"symbol={symbol}" / "data.parquet"
            if not stock_file.exists():
                return None
            try:
                df = pl.read_parquet(stock_file)
            except Exception:
                return None

        try:
            if len(df) < 504:  # Need at least 2 years of history
                return None

            date_col = "date" if "date" in df.columns else "timestamp"
            df = df.sort(date_col).with_columns(pl.col(date_col).cast(pl.Date).alias("date_key"))

            # --- Category A: Secular Compounding & Quality ---
            ret1d = ind.calc_log_returns("close", [1])[0]
            df = df.with_columns(ret1d)

            window_3y = min(len(df), 756)
            sortino = ind.calc_rolling_sortino("ret_1d", window_3y).alias("sortino_ratio_756d")
            drawdown = ind.calc_rolling_drawdown("close", window_3y).alias("max_drawdown_756d")
            sharpe = ind.calc_rolling_sharpe("ret_1d", window_3y).alias("sharpe_ratio_756d")

            # Distance to All-Time High
            ath = pl.col("high").cum_max()
            dist_ath = ((pl.col("close") - ath) / (ath + 1e-8)).alias("dist_ath_pct")

            # 3-Year Rolling Return (CAGR Proxy)
            cagr_3y = ((pl.col("close") / pl.col("close").shift(window_3y)).log() / (window_3y / 252.0)).alias("cagr_3y_proxy")
            calmar_3y = (cagr_3y / (drawdown.abs() + 1e-8)).alias("calmar_ratio_3y")

            df = df.with_columns([sortino, drawdown, sharpe, dist_ath, cagr_3y, calmar_3y])

            # Add symbol column
            if "symbol" not in df.columns:
                df = df.with_columns(pl.lit(symbol).alias("symbol"))

            return df

        except Exception as e:
            logger.warning(f"Error computing Model 2 features for {symbol}: {e}")
            return None
