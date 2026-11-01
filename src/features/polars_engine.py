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
from src.features.feature_engineer_model4 import Model4FeatureEngineer

logger = logging.getLogger("PolarsFeatureEngine")

class PolarsFeatureEngine:
    """
    Master Vectorized Feature Engineering Engine.
    Processes the entire Indian Equity Universe (2,357 stocks) in parallel
    and writes partitioned Parquet feature tables into the 5 decoupled Gold Stores:
      - Model 0: gold/features_screener_ranking/ (28 features)
      - Model 1: gold/features_short_term_positional/ (25 features)
      - Model 2: gold/features_long_term_swing/ (25 features)
      - Model 3: gold/features_price_corridor/ (20 features)
      - Model 4: gold/features_stock_action_classifier/ (22 features)
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.gold_model0_dir = settings.GOLD_DIR / "features_screener_ranking"
        self.gold_model1_dir = settings.GOLD_DIR / "features_short_term_positional"
        self.gold_model2_dir = settings.GOLD_DIR / "features_long_term_swing"
        self.gold_model3_dir = settings.GOLD_DIR / "features_price_corridor"
        self.gold_model4_dir = settings.GOLD_DIR / "features_stock_action_classifier"

        for d in [self.gold_model0_dir, self.gold_model1_dir, self.gold_model2_dir, self.gold_model3_dir, self.gold_model4_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing 5 specialized Feature Engineers...")
        self.m0 = Model0FeatureEngineer()
        self.m1 = Model1FeatureEngineer()
        self.m2 = Model2FeatureEngineer()
        self.m3 = Model3FeatureEngineer()
        self.m4 = Model4FeatureEngineer()

    def process_all_stocks(self, limit: Optional[int] = None, force_models: Optional[List[int]] = None):
        """Processes all stocks across the universe and builds the Gold Feature lakehouse."""
        force_set = set(force_models or [])
        exchange_dir = self.silver_ohlcv_dir / "exchange=NSE"
        stock_dirs = sorted(list(exchange_dir.glob("symbol=*")))
        if limit:
            stock_dirs = stock_dirs[:limit]

        total = len(stock_dirs)
        logger.info(f"Starting Gold Feature Extraction for {total} stocks across ALL 5 MODELS (forced={force_set})...")
        start_time = time.time()
        
        m0_count = m1_count = m2_count = m3_count = m4_count = 0
        total_bars = 0

        for idx, sdir in enumerate(stock_dirs, 1):
            symbol = sdir.name.split("=")[-1]
            parquet_file = sdir / "data.parquet"
            if not parquet_file.exists():
                continue

            try:
                # Read stock data ONCE into memory
                df = pl.read_parquet(parquet_file)
                if len(df) == 0:
                    continue

                # 1. Model 0 Features (Pre-Market Screener)
                m0_file = self.gold_model0_dir / f"{symbol}.parquet"
                if 0 in force_set or not m0_file.exists():
                    df0 = self.m0.compute_for_stock(symbol, df)
                    if df0 is not None and len(df0) > 0:
                        df0.write_parquet(m0_file, compression="zstd")
                if m0_file.exists():
                    m0_count += 1
                    total_bars += len(df)

                # 2. Model 1 Features (Positional Swing < 1 Year)
                m1_file = self.gold_model1_dir / f"{symbol}.parquet"
                if 1 in force_set or not m1_file.exists():
                    df1 = self.m1.compute_for_stock(symbol, df)
                    if df1 is not None and len(df1) > 0:
                        df1.write_parquet(m1_file, compression="zstd")
                if m1_file.exists():
                    m1_count += 1

                # 3. Model 2 Features (Wealth Compounding > 1 Year)
                m2_file = self.gold_model2_dir / f"{symbol}.parquet"
                if 2 in force_set or not m2_file.exists():
                    df2 = self.m2.compute_for_stock(symbol, df)
                    if df2 is not None and len(df2) > 0:
                        df2.write_parquet(m2_file, compression="zstd")
                if m2_file.exists():
                    m2_count += 1

                # 4. Model 3 Features (Price Corridors)
                m3_file = self.gold_model3_dir / f"{symbol}.parquet"
                if 3 in force_set or not m3_file.exists():
                    df3 = self.m3.compute_for_stock(symbol, df)
                    if df3 is not None and len(df3) > 0:
                        df3.write_parquet(m3_file, compression="zstd")
                if m3_file.exists():
                    m3_count += 1

                # 5. Model 4 Features (Universal Stock Action & Confidence Classifier)
                m4_file = self.gold_model4_dir / f"{symbol}.parquet"
                if 4 in force_set or not m4_file.exists():
                    df4 = self.m4.compute_for_stock(symbol, df)
                    if df4 is not None and len(df4) > 0:
                        df4.write_parquet(m4_file, compression="zstd")
                if m4_file.exists():
                    m4_count += 1

                if idx % 200 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = total_bars / max(elapsed, 0.001)
                    logger.info(
                        f"Progress: [{idx}/{total}] stocks | M0:{m0_count} M1:{m1_count} M2:{m2_count} M3:{m3_count} M4:{m4_count} | "
                        f"{rate:,.0f} bars/sec"
                    )

            except Exception as e:
                logger.warning(f"Error processing {symbol}: {e}")

        total_time = time.time() - start_time
        logger.info("=" * 70)
        logger.info(f"PHASE 2 MASTER FEATURE PIPELINE (5 MODELS) COMPLETE!")
        logger.info(f"Model 0 (Screener): {m0_count}/{total} stocks in Gold")
        logger.info(f"Model 1 (Positional < 1Y): {m1_count}/{total} stocks in Gold")
        logger.info(f"Model 2 (Compounding > 1Y): {m2_count}/{total} stocks in Gold")
        logger.info(f"Model 3 (Price Corridors): {m3_count}/{total} stocks in Gold")
        logger.info(f"Model 4 (Action & Confidence): {m4_count}/{total} stocks in Gold")
        logger.info(f"Total Bars Processed: {total_bars:,} in {total_time:.2f}s ({total_bars/max(total_time, 0.001):,.0f} bars/sec)")
        logger.info("=" * 70)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    engine = PolarsFeatureEngine()
    engine.process_all_stocks()
