import logging
import polars as pl
from pathlib import Path
from typing import Optional
from src.config.settings import settings
import src.features.polars_indicators as ind

logger = logging.getLogger(__name__)

class Model1FeatureEngineer:
    """
    Computes the 25 intermediate cyclical & momentum features for Model 1
    (Positional & Swing Alpha Engine - Holding Horizon: < 1 Year / 1 to 9 Months).
    Writes to data/lakehouse/gold/features_short_term_positional/
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.silver_macro_dir = settings.SILVER_DIR / "macro"
        self.silver_master_dir = settings.SILVER_DIR / "master"
        self.gold_output_dir = settings.GOLD_DIR / "features_short_term_positional"
        self.gold_output_dir.mkdir(parents=True, exist_ok=True)

    def compute_for_stock(self, symbol: str, df: Optional[pl.DataFrame] = None) -> Optional[pl.DataFrame]:
        """Computes Model 1's 25-feature matrix for a single stock."""
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

            # --- Category A: Intermediate Momentum & Trend ---
            ret_exprs = ind.calc_log_returns("close", [21, 63, 126])
            ema50 = ind.calc_ema("close", 50)
            ema200 = ind.calc_ema("close", 200)
            atr20 = ind.calc_atr("high", "low", "close", 20)
            adx14 = ind.calc_adx("high", "low", "close", 14)

            df = df.with_columns(ret_exprs + [ema50, ema200, atr20, adx14])

            dist_ema50 = ind.calc_distance_to_ema_atr("close", "ema_50", "atr_20", "dist_ema50_atr")
            dist_ema200 = ind.calc_distance_to_ema_atr("close", "ema_200", "atr_20", "dist_ema200_atr")

            # --- Category B: Trend Persistence & Quality ---
            vr60 = ind.calc_variance_ratio("close", 1, 5, 60)
            sharpe63 = ind.calc_rolling_sharpe("ret_21d", 63)

            # --- Category C: Volatility & Breakout Structure ---
            parkinson60 = ind.calc_parkinson_volatility("high", "low", 60)
            bb_exprs = ind.calc_bollinger_bands("close", 20, 2.0)
            dist_52w = ((pl.col("close") - pl.col("high").rolling_max(252)) / (pl.col("high").rolling_max(252) + 1e-8)).alias("dist_52w_high_pct")

            df = df.with_columns([dist_ema50, dist_ema200, vr60, sharpe63, parkinson60, dist_52w] + bb_exprs)

            # Add symbol column
            if "symbol" not in df.columns:
                df = df.with_columns(pl.lit(symbol).alias("symbol"))

            return df

        except Exception as e:
            logger.warning(f"Error computing Model 1 features for {symbol}: {e}")
            return None
