import sys
import time
import argparse
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.master.security_master import SecurityMaster
from src.crawler.intraday_1m_backfill import Intraday1mBackfiller
from scripts.bulk_backfill_all import TOP_PRIORITY_SYMBOLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("IntradayBulkRunner")

def run_intraday_backfill(mode: str = "priority", months: int = 12):
    logger.info("=" * 70)
    logger.info(f"STARTING 1-YEAR 1-MINUTE INTRADAY BACKFILL (Mode: {mode}, Months: {months})")
    logger.info("=" * 70)

    sec_master = SecurityMaster()
    if sec_master.df is None:
        logger.error("Master Securities Parquet not found!")
        return

    backfiller = Intraday1mBackfiller()
    
    # 1. Login to SmartAPI
    logger.info("Logging into Angel One SmartAPI...")
    if not backfiller.angel.login():
        logger.error("Authentication failed. Check credentials in .env")
        return

    # 2. Determine Symbol Queue
    completed = backfiller.get_completed_symbols()
    logger.info(f"Found {len(completed)} previously completed stocks in checkpoint log.")

    if mode == "priority":
        target_symbols = [s for s in TOP_PRIORITY_SYMBOLS if s not in completed]
        logger.info(f"Targeting Top Blue Chips: {len(target_symbols)} remaining.")
    else:
        all_syms = sec_master.df["nse_symbol"].drop_nulls().to_list()
        target_symbols = [s for s in all_syms if s not in completed]
        logger.info(f"Targeting Full Universe: {len(target_symbols)} remaining stocks.")

    # 3. Process Stocks Sequentially with strict Rate Limiting
    total = len(target_symbols)
    success_count = 0
    t0 = time.time()

    for idx, sym in enumerate(target_symbols, 1):
        sec = sec_master.get_by_symbol(sym)
        if not sec:
            continue
        
        token = sec.get("nse_token")
        if not token:
            logger.warning(f"[{idx}/{total}] {sym:12} | No token found. Skipping.")
            continue

        try:
            sym_t0 = time.time()
            sym, success, count, msg = backfiller.backfill_symbol(
                symbol=sym,
                token=str(token),
                months_back=months,
                resample_to_5m=True
            )
            sym_elapsed = time.time() - sym_t0

            if success:
                success_count += 1
                logger.info(f"[{idx}/{total}] {sym:12} | {count:6} candles | {sym_elapsed:4.1f}s | {msg}")
            else:
                logger.warning(f"[{idx}/{total}] {sym:12} | FAILED: {msg}")
        except Exception as e:
            logger.error(f"[{idx}/{total}] {sym:12} | Unhandled error: {e}. Pausing 3s and continuing...")
            time.sleep(3.0)

        if idx % 50 == 0:
            elapsed_min = (time.time() - t0) / 60
            logger.info(f"--> Checkpoint: {idx}/{total} processed in {elapsed_min:.1f} mins ({success_count} success)")

    total_min = (time.time() - t0) / 60
    logger.info("=" * 70)
    logger.info(f"INTRADAY BACKFILL FINISHED: {success_count}/{total} in {total_min:.1f} mins!")
    logger.info("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="1-Minute Historical Candle Backfiller")
    parser.add_argument("--mode", choices=["priority", "all"], default="priority", help="priority (top blue chips) or all (2,357 stocks)")
    parser.add_argument("--months", type=int, default=12, help="Number of months back (default: 12)")
    args = parser.parse_args()

    run_intraday_backfill(mode=args.mode, months=args.months)

