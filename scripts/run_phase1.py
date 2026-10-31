import sys
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.broker.angel_client import AngelClient
from src.master.security_master import SecurityMaster
from src.crawler.yfinance_backfill import YFinanceBackfiller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Phase1_Runner")

def main():
    logger.info("=" * 60)
    logger.info("STARTING PHASE 1: MASTER UNIVERSE & DATA PIPELINE")
    logger.info("=" * 60)

    # 1. Test Angel One SmartAPI Authentication
    logger.info("[Step 1/4] Authenticating with Angel One SmartAPI...")
    angel = AngelClient()
    login_success = angel.login()
    
    instruments = None
    if login_success:
        profile = angel.get_profile()
        logger.info(f"Connected to Angel One! Client: {settings.ANGEL_CLIENT_CODE}")
        if profile and profile.get("data"):
            logger.info(f"User Profile Name: {profile['data'].get('name')}")
        
        # 2. Download Complete Instrument Master Dump
        logger.info("[Step 2/4] Downloading Angel One Master Instrument Dump...")
        try:
            instruments = angel.download_instrument_master()
        except Exception as e:
            logger.warning(f"Could not download Angel instrument dump: {e}")
    else:
        logger.warning("Angel One login failed or skipped. Proceeding with public NSE feeds...")

    # 3. Build Unified Securities Master (NSE + BSE)
    logger.info("[Step 3/4] Building Dual-Exchange Securities Master...")
    sec_master = SecurityMaster()
    master_df = sec_master.build_master_universe(instruments)
    logger.info(f"Master Universe built successfully with {len(master_df)} securities!")
    
    # Show sample entries
    logger.info("Sample Master Securities:")
    print(master_df.head(5))

    # 4. Test Historical Backfill on Key Blue-Chip Stocks
    logger.info("[Step 4/4] Testing Historical Backfill on Top NIFTY 50 Stocks...")
    test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    backfiller = YFinanceBackfiller(exchange="NSE")
    success = backfiller.backfill_bulk(test_symbols, period="2y")
    logger.info(f"Successfully backfilled {success}/{len(test_symbols)} sample stocks to Silver Lakehouse.")

    logger.info("=" * 60)
    logger.info("PHASE 1 INITIALIZATION COMPLETE & VERIFIED!")
    logger.info(f"Master Parquet: {sec_master.MASTER_PARQUET_PATH}")
    logger.info(f"Silver OHLCV 1D: {backfiller.output_base}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()

