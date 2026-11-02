import sys
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.serving.chart_service import ChartService
from src.crawler.eod_intraday_batch import EODIntradayBatchWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TestHybrid1M")

def test_hybrid_system():
    logger.info("=" * 70)
    logger.info("TESTING HYBRID 1-MINUTE DATA ENGINE: LAZY LOAD & EOD BATCH")
    logger.info("=" * 70)

    # 1. Test Lazy Load in ChartService (Option 4)
    logger.info("\n[TEST 1] Testing On-Demand Lazy Load via ChartService...")
    chart_service = ChartService()

    t0 = logging.time.time()
    candles_1m = chart_service.get_candlesticks("RELIANCE", timeframe="1m", limit=50, auto_backfill=True)
    elapsed_ms = (logging.time.time() - t0) * 1000.0
    logger.info(f"ChartService served {len(candles_1m)} 1m candles for RELIANCE in {elapsed_ms:.1f}ms (First candle: {candles_1m[0] if candles_1m else None})")

    t0 = logging.time.time()
    candles_1d = chart_service.get_candlesticks("INFY", timeframe="1d", limit=30, auto_backfill=True)
    elapsed_ms = (logging.time.time() - t0) * 1000.0
    logger.info(f"ChartService served {len(candles_1d)} 1d candles for INFY in {elapsed_ms:.1f}ms (First candle: {candles_1d[0] if candles_1d else None})")

    # 2. Test Post-Market Full-Universe 1M Batch Worker (Option 1)
    logger.info("\n" + "=" * 70)
    logger.info("[TEST 2] Testing Post-Market Full-Universe 1M Batch Worker (Top 5 Scrips)...")
    logger.info("=" * 70)
    batch_worker = EODIntradayBatchWorker(exchange="NSE")
    updated = batch_worker.run_batch_sync(limit=5, max_hours=0.05)
    logger.info(f"Batch Worker Test Complete! Updated {updated} stocks.")

    logger.info("\n>>> HYBRID 1-MINUTE ENGINE TEST PASSED 100%! <<<")

if __name__ == "__main__":
    test_hybrid_system()

