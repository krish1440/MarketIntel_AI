import sys
import time
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.master.security_master import SecurityMaster
from src.crawler.daily_sync import DailySyncer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DailySyncRunner")

def main():
    logger.info("=" * 65)
    logger.info("RUNNING EOD INCREMENTAL DAILY SYNC")
    logger.info("=" * 65)

    sec_master = SecurityMaster()
    if sec_master.df is None:
        logger.error("Master Securities Parquet not found!")
        return

    symbols = sec_master.df["nse_symbol"].drop_nulls().to_list()
    logger.info(f"Checking for daily updates across {len(symbols)} stocks...")

    syncer = DailySyncer(exchange="NSE")
    t0 = time.time()
    
    updated, up_to_date = syncer.sync_bulk(symbols, max_workers=12)
    elapsed = time.time() - t0

    logger.info("=" * 65)
    logger.info(f"SYNC FINISHED IN {elapsed:.1f} SECONDS!")
    logger.info(f"Stocks Updated with New Day(s): {updated}")
    logger.info(f"Stocks Already Up-to-Date:      {up_to_date}")
    logger.info("=" * 65)

if __name__ == "__main__":
    main()

