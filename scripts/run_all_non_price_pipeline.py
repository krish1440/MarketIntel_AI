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
from src.crawler.fii_dii_crawler import FiiDiiCrawler
from src.crawler.nse_delivery_crawler import NseDeliveryCrawler
from src.crawler.corporate_calendar import CorporateCalendarCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NonPricePipeline")

def main():
    logger.info("=" * 75)
    logger.info("LAUNCHING UNIFIED NON-PRICE DATA PIPELINE (OPTION B)")
    logger.info("=" * 75)
    t0 = time.time()

    # 1. Macro & Sector Indices (16 Sectors + India VIX + Nifty Benchmarks)
    logger.info("\n[1/5] Backfilling All 16 Sector Indices, India VIX & Nifty 50...")
    macro_bf = MacroIndicesBackfiller()
    macro_res = macro_bf.backfill_all()

    # 2. Stock-to-Sector Zero-Null Mapper
    logger.info("\n[2/5] Building Stock-to-Sector Mapping (Zero-Null Guarantee)...")
    sec_mapper = SectorMapper()
    mapped_df = sec_mapper.map_all_securities()

    # 3. FII & DII Cash Market Daily Flows
    logger.info("\n[3/5] Crawling FII & DII Historical Net Cash Flows...")
    fii_crawler = FiiDiiCrawler()
    fii_df = fii_crawler.fetch_historical_fii_dii()

    # 4. NSE Security-Wise Delivery Volume % Bhavcopies
    logger.info("\n[4/5] Crawling NSE Security-Wise Delivery Volume & Delivery %...")
    deliv_crawler = NseDeliveryCrawler()
    deliv_df = deliv_crawler.crawl_recent_delivery_history(days_back=15)

    # 5. Corporate Actions & Earnings Calendar
    logger.info("\n[5/5] Fetching Corporate Actions & Earnings Calendar...")
    corp_crawler = CorporateCalendarCrawler()
    corp_df = corp_crawler.fetch_corporate_calendar()

    elapsed = time.time() - t0
    logger.info("=" * 75)
    logger.info(f"UNIFIED NON-PRICE PIPELINE COMPLETE IN {elapsed:.1f} SECONDS!")
    logger.info(f"1. Sector Indices Stored:      {sum(1 for s, _, _ in macro_res.values() if s)}/{len(macro_res)}")
    logger.info(f"2. Stocks Mapped (0% Nulls):   {len(mapped_df)}")
    logger.info(f"3. FII/DII Days Logged:        {len(fii_df)}")
    logger.info(f"4. Delivery Records Cached:    {len(deliv_df)}")
    logger.info(f"5. Corporate Events Cached:    {len(corp_df)}")
    logger.info("=" * 75)

if __name__ == "__main__":
    main()

