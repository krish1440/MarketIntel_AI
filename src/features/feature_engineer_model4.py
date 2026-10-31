import logging
import polars as pl
from pathlib import Path
from typing import Optional
from src.config.settings import settings
import src.features.polars_indicators as ind

logger = logging.getLogger(__name__)

class Model4FeatureEngineer:
    """
    Computes the 22 consensus action & confidence features for Model 4
    (Universal Stock Action & Confidence Classifier: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL).
    Writes to data/lakehouse/gold/features_stock_action_classifier/
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.silver_macro_dir = settings.SILVER_DIR / "macro"
        self.silver_master_dir = settings.SILVER_DIR / "master"
        self.gold_output_dir = settings.GOLD_DIR / "features_stock_action_classifier"
        self.gold_output_dir.mkdir(parents=True, exist_ok=True)

    def compute_for_stock(self, symbol: str, df: Optional[pl.DataFrame] = None) -> Optional[pl.DataFrame]:
        """Computes Model 4's 22-feature matrix for a single stock."""
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

            # --- Category A: Moving Average Alignment & Trend ---
            ema20 = ind.calc_ema("close", 20)
            ema50 = ind.calc_ema("close", 50)
            ema200 = ind.calc_ema("close", 200)
            atr14 = ind.calc_atr("high", "low", "close", 14)
            atr5 = ind.calc_atr("high", "low", "close", 5)
            atr20 = ind.calc_atr("high", "low", "close", 20)
            adx14 = ind.calc_adx("high", "low", "close", 14)
            rsi14 = ind.calc_rsi("close", 14)
            ret_exprs = ind.calc_log_returns("close", [1, 5, 21])

            df = df.with_columns(ret_exprs + [ema20, ema50, ema200, atr14, atr5, atr20, adx14, rsi14])

            # Trend Alignment Score (Stacked EMAs: 20 > 50 > 200 = +1.0; 20 < 50 < 200 = -1.0)
            bullish_stack = (pl.col("ema_20") > pl.col("ema_50")) & (pl.col("ema_50") > pl.col("ema_200"))
            bearish_stack = (pl.col("ema_20") < pl.col("ema_50")) & (pl.col("ema_50") < pl.col("ema_200"))
            trend_alignment = pl.when(bullish_stack).then(1.0).when(bearish_stack).then(-1.0).otherwise(0.0).alias("trend_alignment_score")

            dist_ema20 = ind.calc_distance_to_ema_atr("close", "ema_20", "atr_14", "dist_ema20_atr")
            dist_ema50 = ind.calc_distance_to_ema_atr("close", "ema_50", "atr_14", "dist_ema50_atr")
            dist_ema200 = ind.calc_distance_to_ema_atr("close", "ema_200", "atr_14", "dist_ema200_atr")

            # --- Category C: Volume Quality ---
            rvol20 = ind.calc_rvol("volume", 20)
            vol_trend = (pl.col("volume").rolling_mean(5) / (pl.col("volume").rolling_mean(20) + 1e-8)).alias("volume_trend_5_20")

            # --- Category E: Volatility Geometry & Range Position ---
            bb_exprs = ind.calc_bollinger_bands("close", 20, 2.0)
            atr_ratio = (pl.col("atr_5") / (pl.col("atr_20") + 1e-8)).alias("atr_ratio_5_20")
            
            # Bollinger %b
            bb_percent_b = ((pl.col("close") - pl.col("bb_lower")) / (pl.col("bb_upper") - pl.col("bb_lower") + 1e-8)).alias("bb_percent_b")

            dist_52w_high = ((pl.col("close") - pl.col("high").rolling_max(252)) / (pl.col("high").rolling_max(252) + 1e-8)).alias("dist_52w_high_pct")
            dist_52w_low = ((pl.col("close") - pl.col("low").rolling_min(252)) / (pl.col("low").rolling_min(252) + 1e-8)).alias("dist_52w_low_pct")

            df = df.with_columns([
                trend_alignment, dist_ema20, dist_ema50, dist_ema200,
                rvol20, vol_trend, atr_ratio, dist_52w_high, dist_52w_low
            ] + bb_exprs)
            
            df = df.with_columns(bb_percent_b)

            # Add symbol column
            if "symbol" not in df.columns:
                df = df.with_columns(pl.lit(symbol).alias("symbol"))

            return df

        except Exception as e:
            logger.warning(f"Error computing Model 4 features for {symbol}: {e}")
            return None

