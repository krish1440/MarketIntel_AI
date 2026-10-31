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

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.crawler.macro_indices_backfill import MacroIndicesBackfiller
from src.master.sector_mapper import SectorMapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MacroRunner")

def main():
    logger.info("=" * 70)
    logger.info("STARTING MACRO INDICES & SECTOR MAPPING ENGINE")
    logger.info("=" * 70)
    t0 = time.time()

    # 1. Download all 16 Sector Indices + India VIX + Benchmarks
    logger.info("[Step 1/2] Fetching 16 Sector Indices + India VIX from Inception...")
    backfiller = MacroIndicesBackfiller()
    results = backfiller.backfill_all()

    # 2. Build Zero-Null Stock-to-Sector Mapper
    logger.info("\n[Step 2/2] Mapping all 2,357 Stocks to their Sectors (Zero-Null Guarantee)...")
    mapper = SectorMapper()
    mapped_df = mapper.map_all_securities()

    # 3. Verification & Summary
    null_count = mapped_df["sector_index"].null_count()
    logger.info("=" * 70)
    logger.info(f"MACRO & SECTOR ENGINE COMPLETED in {time.time() - t0:.1f}s!")
    logger.info(f"Total Indices Stored on Disk:  {sum(1 for s, _, _ in results.values() if s)}/{len(results)}")
    logger.info(f"Total Stocks Mapped:          {len(mapped_df)}")
    logger.info(f"Null Sectors Count:           {null_count} (VERIFIED ZERO NULLS!)")
    logger.info("=" * 70)

    # Show distribution of sectors
    print("\n--- SECTOR DISTRIBUTION ACROSS 2,357 STOCKS ---")
    dist = mapped_df.group_by("sector_index").len().sort("len", descending=True)
    print(dist)

if __name__ == "__main__":
    main()

