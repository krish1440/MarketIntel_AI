import logging
import math
import polars as pl
from pathlib import Path
from typing import Optional
from src.config.settings import settings
import src.features.polars_indicators as ind

logger = logging.getLogger(__name__)

class Model3FeatureEngineer:
    """
    Computes the 20 volatility, variance structure & price corridor features for Model 3
    (Probabilistic Price Corridor Forecaster - Horizones: 21D, 63D, 252D).
    Writes to data/lakehouse/gold/features_price_corridor/
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.silver_macro_dir = settings.SILVER_DIR / "macro"
        self.gold_output_dir = settings.GOLD_DIR / "features_price_corridor"
        self.gold_output_dir.mkdir(parents=True, exist_ok=True)

    def compute_for_stock(self, symbol: str, df: Optional[pl.DataFrame] = None) -> Optional[pl.DataFrame]:
        """Computes Model 3's 20-feature volatility corridor matrix for a single stock."""
        if df is None:
            stock_file = self.silver_ohlcv_dir / "exchange=NSE" / f"symbol={symbol}" / "data.parquet"
            if not stock_file.exists():
                return None
            try:
                df = pl.read_parquet(stock_file)
            except Exception:
                return None

        try:
            if len(df) < 126:
                return None

            date_col = "date" if "date" in df.columns else "timestamp"
            df = df.sort(date_col).with_columns(pl.col(date_col).cast(pl.Date).alias("date_key"))

            # --- Category A: Multi-Scale Volatility Estimators ---
            parkinson20 = ind.calc_parkinson_volatility("high", "low", 20)
            garman_klass20 = ind.calc_garman_klass_volatility("open", "high", "low", "close", 20)
            atr14 = ind.calc_atr("high", "low", "close", 14)

            # Volatility Cones (Square Root of Time Expansion)
            atr_cone_21d = (pl.col("atr_14") * math.sqrt(21.0)).alias("atr_cone_21d")
            atr_cone_63d = (pl.col("atr_14") * math.sqrt(63.0)).alias("atr_cone_63d")
            atr_cone_252d = (pl.col("atr_14") * math.sqrt(252.0)).alias("atr_cone_252d")

            # --- Category B: Keltner Channels & Bollinger Squeeze ---
            kc_exprs = ind.calc_keltner_channels("high", "low", "close", 20, 2.0)
            bb_exprs = ind.calc_bollinger_bands("close", 20, 2.0)

            # Z-score of price relative to 50 SMA
            sma50 = ind.calc_sma("close", 50)
            std50 = pl.col("close").rolling_std(window_size=50)
            zscore_sma50 = ((pl.col("close") - pl.col("sma_50")) / (std50 + 1e-8)).alias("zscore_from_sma50")

            df = df.with_columns([
                parkinson20, garman_klass20, atr14, sma50
            ])
            df = df.with_columns([
                atr_cone_21d, atr_cone_63d, atr_cone_252d, zscore_sma50
            ] + kc_exprs + bb_exprs)

            # Add symbol column
            if "symbol" not in df.columns:
                df = df.with_columns(pl.lit(symbol).alias("symbol"))

            return df

        except Exception as e:
            logger.warning(f"Error computing Model 3 features for {symbol}: {e}")
            return None
