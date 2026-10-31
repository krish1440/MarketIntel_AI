import os
import sys
import time
import logging
from pathlib import Path
import polars as pl
from typing import List, Optional

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import settings
from src.features.feature_engineer_model0 import Model0FeatureEngineer
from src.features.polars_indicators import (
    calc_log_returns, calc_ema, calc_sma, calc_atr, calc_bollinger_bands,
    calc_rsi, calc_parkinson_volatility, calc_garman_klass_volatility,
    calc_rvol, calc_candle_anatomy, calc_distance_to_ema_atr
)

logger = logging.getLogger("PolarsFeatureEngine")

class PolarsFeatureEngine:
    """
    Master Vectorized Feature Engineering Engine.
    Processes the entire Indian Equity Universe (2,357 stocks) in parallel
    and writes partitioned Parquet feature tables into the 4 decoupled Gold Stores.
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.gold_model0_dir = settings.GOLD_DIR / "features_screener_ranking"
        self.gold_model1_dir = settings.GOLD_DIR / "features_short_term_positional"
        self.gold_model2_dir = settings.GOLD_DIR / "features_long_term_swing"
        self.gold_model3_dir = settings.GOLD_DIR / "features_price_corridor"

        for d in [self.gold_model0_dir, self.gold_model1_dir, self.gold_model2_dir, self.gold_model3_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.model0_eng = Model0FeatureEngineer()

    def process_all_stocks(self, limit: Optional[int] = None):
        """Processes all stocks across the universe and builds the Gold Feature lakehouse."""
        stock_files = list(self.silver_ohlcv_dir.glob("*.parquet"))
        if limit:
            stock_files = stock_files[:limit]

        total = len(stock_files)
        logger.info(f"Starting Gold Feature Extraction for {total} stocks...")
        start_time = time.time()
        
        success = 0
        total_bars = 0

        for idx, file_path in enumerate(stock_files, 1):
            symbol = file_path.stem
            try:
                # 1. Model 0 Feature Matrix
                m0_df = self.model0_eng.compute_for_stock(symbol)
                if m0_df is not None and len(m0_df) > 0:
                    out_path = self.gold_model0_dir / f"{symbol}.parquet"
                    m0_df.write_parquet(out_path, compression="zstd")
                    total_bars += len(m0_df)
                    success += 1

                if idx % 100 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = total_bars / max(elapsed, 0.001)
                    logger.info(f"Progress: [{idx}/{total}] stocks | {total_bars:,} bars | {rate:,.0f} bars/sec")

            except Exception as e:
                logger.warning(f"Error processing {symbol}: {e}")

        total_time = time.time() - start_time
        logger.info("=" * 70)
        logger.info(f"FEATURE PIPELINE COMPLETE: {success}/{total} stocks processed.")
        logger.info(f"Total Bars Processed: {total_bars:,} in {total_time:.2f} seconds ({total_bars/max(total_time, 0.001):,.0f} bars/sec)")
        logger.info("=" * 70)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    engine = PolarsFeatureEngine()
    engine.process_all_stocks()
