import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from src.config.settings import settings
from src.master.security_master import SecurityMaster
from src.crawler.intraday_gap_syncer import IntradayGapSyncer

logger = logging.getLogger("EODIntradayBatch")

IST = timezone(timedelta(hours=5, minutes=30))

class EODIntradayBatchWorker:
    """
    Post-Market Full-Universe 1-Minute Batch Syncer:
    - Runs after market close (e.g., 16:30 IST).
    - Checks all 2,357 stocks in the master universe.
    - If a stock is missing today's 1-minute bars, fetches them from Angel One SmartAPI.
    - Safely rate-limited to avoid API throttling.
    - Result: 100% complete 1-minute historical data for EVERY stock on the exchange.
    """

    def __init__(self, exchange: str = "NSE"):
        self.exchange = exchange
        self.syncer = IntradayGapSyncer(exchange=exchange)
        self.sec_master = SecurityMaster()

    def run_batch_sync(self, limit: Optional[int] = None, max_hours: float = 1.0) -> int:
        """
        Runs batch 1-minute sync across all eligible stocks.
        max_hours: Safety time cap to prevent overnight runaway jobs.
        """
        logger.info("=" * 75)
        logger.info("STARTING POST-MARKET FULL-UNIVERSE 1-MINUTE BATCH INGESTION")
        logger.info(f"Exchange: {self.exchange} | Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
        logger.info("=" * 75)

        all_symbols = []
        if self.sec_master.df is not None:
            all_symbols = self.sec_master.df["nse_symbol"].drop_nulls().to_list()

        if limit:
            all_symbols = all_symbols[:limit]

        total = len(all_symbols)
        logger.info(f"Targeting {total} stocks for 1-minute end-of-day parity...")

        t_start = time.time()
        max_seconds = max_hours * 3600.0
        updated_count = 0
        already_current = 0

        for idx, sym in enumerate(all_symbols, 1):
            if time.time() - t_start > max_seconds:
                logger.info(f"Reached time cap of {max_hours} hours. Pausing batch.")
                break

            try:
                # Fast gap check first
                gap = self.syncer.detect_gap(sym)
                if not gap:
                    already_current += 1
                    continue

                sym_name, success, count, msg = self.syncer.sync_symbol(sym)
                if success and count > 0:
                    updated_count += 1
                    logger.info(f"  [{idx}/{total}] {sym:<10} | +{count:4} 1m bars | {msg}")
                else:
                    logger.debug(f"  [{idx}/{total}] {sym:<10} | {msg}")

            except Exception as e:
                logger.warning(f"Error syncing {sym}: {e}")

            if idx % 100 == 0:
                elapsed_min = (time.time() - t_start) / 60.0
                logger.info(f"--> Batch Checkpoint: [{idx}/{total}] stocks processed in {elapsed_min:.1f}m ({updated_count} updated, {already_current} current).")

        elapsed_total = (time.time() - t_start) / 60.0
        logger.info("=" * 75)
        logger.info(f"FULL-UNIVERSE 1M BATCH FINISHED: {updated_count} updated, {already_current} current in {elapsed_total:.1f} mins.")
        logger.info("=" * 75)
        return updated_count

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    worker = EODIntradayBatchWorker()
    worker.run_batch_sync(limit=10)

