import sys
import logging
from pathlib import Path
import polars as pl

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
from src.crawler.yfinance_backfill import YFinanceBackfiller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("BulkBackfill")

# High-priority index constituents (NIFTY 50 & Top Blue Chips) to download first
TOP_PRIORITY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "SBIN",
    "ITC", "HINDUNILVR", "LT", "BAJFINANCE", "HCLTECH", "MARUTI", "SUNPHARMA",
    "ADANIENT", "KOTAKBANK", "TITAN", "ONGC", "TATAMOTORS", "NTPC", "AXISBANK",
    "POWERGRID", "M&M", "ADANIPORTS", "ULTRACEMCO", "COALINDIA", "BAJAJFINSV",
    "ASIANPAINT", "WIPRO", "NESTLEIND", "JSWSTEEL", "GRASIM", "TECHM", "TATASTEEL",
    "LTIM", "SBILIFE", "HDFCLIFE", "CIPLA", "BRITANNIA", "HINDALCO", "EICHERMOT",
    "TATACONSUM", "DRREDDY", "APOLLOHOSP", "DIVISLAB", "BAJAJ-AUTO", "HEROMOTOCO",
    "BPCL", "SHRIRAMFIN", "TRENT", "BEL", "HAL", "ZOMATO", "JIOFIN", "VEDL"
]

def main(overwrite=True):
    logger.info("=" * 70)
    logger.info("STARTING INCEPTION-TO-DATE BULK HISTORICAL BACKFILL (period='max')")
    logger.info("=" * 70)

    # 1. Load Master Universe
    sec_master = SecurityMaster()
    if sec_master.df is None:
        logger.error("Master Securities Parquet not found! Run scripts/run_phase1.py first.")
        return

    all_symbols = sec_master.df["nse_symbol"].drop_nulls().to_list()
    logger.info(f"Loaded {len(all_symbols)} total securities from Master Universe.")

    # 2. Sort symbols so top market cap / blue chips are processed first
    priority_set = set(TOP_PRIORITY_SYMBOLS)
    tier1 = [s for s in TOP_PRIORITY_SYMBOLS if s in all_symbols]
    tier2 = [s for s in all_symbols if s not in priority_set]
    ordered_symbols = tier1 + tier2

    logger.info(f"Queue ordered: Tier 1 ({len(tier1)} Top Blue Chips) -> Tier 2 ({len(tier2)} Broad Equities).")

    # 3. Launch Bulk Downloader
    backfiller = YFinanceBackfiller(exchange="NSE")
    import time
    t0 = time.time()
    
    # Run bulk download (overwrite=True for first 5 stocks to expand from 2y to max, and download all others)
    success, skipped = backfiller.backfill_bulk(
        symbols=ordered_symbols,
        max_workers=8,
        period="max",
        overwrite=overwrite
    )

    elapsed_min = (time.time() - t0) / 60
    logger.info("=" * 70)
    logger.info(f"BULK BACKFILL COMPLETE in {elapsed_min:.1f} minutes!")
    logger.info(f"Downloaded: {success} stocks | Skipped: {skipped} stocks")
    
    # Calculate disk usage
    parquet_files = list(backfiller.output_base.glob("**/data.parquet"))
    total_bytes = sum(f.stat().st_size for f in parquet_files)
    logger.info(f"Total Stock Partitions on Disk: {len(parquet_files)}")
    logger.info(f"Total Lakehouse Storage Used: {total_bytes / (1024 * 1024):.2f} MB")
    logger.info("=" * 70)

if __name__ == "__main__":
    main(overwrite=False)
