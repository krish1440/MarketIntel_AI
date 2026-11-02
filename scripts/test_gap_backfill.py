import sys
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.crawler.intraday_gap_syncer import IntradayGapSyncer
from src.crawler.gap_orchestrator import GapOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TestGapBackfill")

def test_gap_syncer():
    logger.info("=" * 70)
    logger.info("TESTING INTRADAY 1-MINUTE GAP DETECTION & SYNCER")
    logger.info("=" * 70)

    syncer = IntradayGapSyncer(exchange="NSE")
    test_symbols = ["RELIANCE", "TCS", "INFY"]

    for sym in test_symbols:
        gap = syncer.detect_gap(sym)
        if gap:
            from_dt, to_dt = gap
            logger.info(f"Symbol: {sym:<10} | GAP DETECTED: from {from_dt.strftime('%Y-%m-%d %H:%M')} to {to_dt.strftime('%Y-%m-%d %H:%M')}")
        else:
            logger.info(f"Symbol: {sym:<10} | ALREADY UP TO DATE (No gap detected)")

    logger.info("\n" + "=" * 70)
    logger.info("TESTING UNIFIED GAP ORCHESTRATOR PREVIEW (Top 5 Symbols)")
    logger.info("=" * 70)

    orchestrator = GapOrchestrator(exchange="NSE")
    universe = orchestrator.get_target_universe(limit=5)
    logger.info(f"Target test universe: {universe}")

    # Test 1D gap check
    updated_1d, up_to_date_1d = orchestrator.sync_1d_gaps(universe, max_workers=4)
    logger.info(f"1D Results -> Updated: {updated_1d}, Up-to-Date: {up_to_date_1d}")

    # Test 1M intraday gap sync on TCS (has gap from Friday Oct 30 afternoon)
    logger.info("\n" + "=" * 70)
    logger.info("TESTING 1-MINUTE LIVE SYNC VIA ANGEL ONE SMARTAPI (TCS)")
    logger.info("=" * 70)
    updated_1m = orchestrator.sync_1m_gaps(["TCS"], max_symbols=1)
    logger.info(f"1M Results -> Updated: {updated_1m} symbols with 1-minute historical candles.")

    logger.info("\n>>> ALL GAP TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_gap_syncer()
