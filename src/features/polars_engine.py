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
from src.features.feature_engineer_model1 import Model1FeatureEngineer
from src.features.feature_engineer_model2 import Model2FeatureEngineer
from src.features.feature_engineer_model3 import Model3FeatureEngineer

logger = logging.getLogger("PolarsFeatureEngine")

class PolarsFeatureEngine:
    """
    Master Vectorized Feature Engineering Engine.
    Processes the entire Indian Equity Universe (2,357 stocks) in parallel
    and writes partitioned Parquet feature tables into the 4 decoupled Gold Stores:
      - Model 0: gold/features_screener_ranking/ (28 features)
      - Model 1: gold/features_short_term_positional/ (25 features)
      - Model 2: gold/features_long_term_swing/ (25 features)
      - Model 3: gold/features_price_corridor/ (20 features)
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.gold_model0_dir = settings.GOLD_DIR / "features_screener_ranking"
        self.gold_model1_dir = settings.GOLD_DIR / "features_short_term_positional"
        self.gold_model2_dir = settings.GOLD_DIR / "features_long_term_swing"
        self.gold_model3_dir = settings.GOLD_DIR / "features_price_corridor"

        for d in [self.gold_model0_dir, self.gold_model1_dir, self.gold_model2_dir, self.gold_model3_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing 4 specialized Feature Engineers...")
        self.m0 = Model0FeatureEngineer()
        self.m1 = Model1FeatureEngineer()
        self.m2 = Model2FeatureEngineer()
        self.m3 = Model3FeatureEngineer()

    def process_all_stocks(self, limit: Optional[int] = None):
        """Processes all stocks across the universe and builds the Gold Feature lakehouse."""
        exchange_dir = self.silver_ohlcv_dir / "exchange=NSE"
        stock_dirs = sorted(list(exchange_dir.glob("symbol=*")))
        if limit:
            stock_dirs = stock_dirs[:limit]

        total = len(stock_dirs)
        logger.info(f"Starting Gold Feature Extraction for {total} stocks across ALL 4 MODELS...")
        start_time = time.time()
        
        m0_count = m1_count = m2_count = m3_count = 0
        total_bars = 0

        for idx, sdir in enumerate(stock_dirs, 1):
            symbol = sdir.name.split("=")[-1]
            parquet_file = sdir / "data.parquet"
            if not parquet_file.exists():
                continue

            # Skip if already generated (resumable)
            m0_file = self.gold_model0_dir / f"{symbol}.parquet"
            if m0_file.exists():
                m0_count += 1
                m1_count += 1
                m2_count += 1
                m3_count += 1
                continue

            try:
                # Read stock data ONCE into memory
                df = pl.read_parquet(parquet_file)
                if len(df) == 0:
                    continue

                # 1. Model 0 Features (Pre-Market Screener)
                df0 = self.m0.compute_for_stock(symbol, df)
                if df0 is not None and len(df0) > 0:
                    df0.write_parquet(self.gold_model0_dir / f"{symbol}.parquet", compression="zstd")
                    m0_count += 1
                    total_bars += len(df0)

                # 2. Model 1 Features (Positional Swing < 1 Year)
                df1 = self.m1.compute_for_stock(symbol, df)
                if df1 is not None and len(df1) > 0:
                    df1.write_parquet(self.gold_model1_dir / f"{symbol}.parquet", compression="zstd")
                    m1_count += 1

                # 3. Model 2 Features (Wealth Compounding > 1 Year)
                df2 = self.m2.compute_for_stock(symbol, df)
                if df2 is not None and len(df2) > 0:
                    df2.write_parquet(self.gold_model2_dir / f"{symbol}.parquet", compression="zstd")
                    m2_count += 1

                # 4. Model 3 Features (Price Corridors)
                df3 = self.m3.compute_for_stock(symbol, df)
                if df3 is not None and len(df3) > 0:
                    df3.write_parquet(self.gold_model3_dir / f"{symbol}.parquet", compression="zstd")
                    m3_count += 1

                if idx % 100 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = total_bars / max(elapsed, 0.001)
                    logger.info(
                        f"Progress: [{idx}/{total}] stocks | M0:{m0_count} M1:{m1_count} M2:{m2_count} M3:{m3_count} | "
                        f"{total_bars:,} bars | {rate:,.0f} bars/sec"
                    )

            except Exception as e:
                logger.warning(f"Error processing {symbol}: {e}")

        total_time = time.time() - start_time
        logger.info("=" * 70)
        logger.info(f"PHASE 2 MASTER FEATURE PIPELINE COMPLETE!")
        logger.info(f"Model 0 (Screener): {m0_count}/{total} stocks generated in Gold")
        logger.info(f"Model 1 (Positional < 1Y): {m1_count}/{total} stocks generated in Gold")
        logger.info(f"Model 2 (Compounding > 1Y): {m2_count}/{total} stocks generated in Gold")
        logger.info(f"Model 3 (Price Corridors): {m3_count}/{total} stocks generated in Gold")
        logger.info(f"Total Bars Processed: {total_bars:,} in {total_time:.2f}s ({total_bars/max(total_time, 0.001):,.0f} bars/sec)")
        logger.info("=" * 70)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    engine = PolarsFeatureEngine()
    engine.process_all_stocks()
