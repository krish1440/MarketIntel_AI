import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import polars as pl

# Ensure UTF-8 output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.broker.angel_client import AngelClient
from src.master.security_master import SecurityMaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("IntradayTester")

def fetch_intraday_sample(symbols=["RELIANCE", "INFY", "TCS"], interval="ONE_MINUTE"):
    sec_master = SecurityMaster()
    angel = AngelClient()
    
    logger.info("Logging into Angel One SmartAPI...")
    if not angel.login():
        logger.error("Failed to authenticate with Angel One.")
        return

    # Date range for recent trading days (last 5 business days)
    # Angel format: 'YYYY-MM-DD HH:MM'
    today = datetime.now()
    # Go back 5 days
    from_dt = (today - timedelta(days=7)).strftime("%Y-%m-%d 09:15")
    to_dt = today.strftime("%Y-%m-%d 15:30")
    
    logger.info(f"Requesting {interval} candles from {from_dt} to {to_dt}...")

    for sym in symbols:
        sec = sec_master.get_by_symbol(sym)
        if not sec:
            logger.warning(f"Symbol {sym} not found in master database!")
            continue

        token = sec.get("nse_token")
        if not token:
            logger.warning(f"No NSE token found for {sym}")
            continue

        logger.info(f"Fetching {interval} data for {sym} (Token: {token})...")
        candles = angel.get_historical_candles(
            exchange="NSE",
            symbol_token=str(token),
            interval=interval,
            from_date=from_dt,
            to_date=to_dt
        )

        if not candles:
            logger.warning(f"No candles returned for {sym}. Response was empty or error.")
            continue

        logger.info(f"Received {len(candles)} intraday candles for {sym}!")
        
        # Angel candle format: [timestamp, open, high, low, close, volume]
        records = []
        for c in candles:
            records.append({
                "timestamp": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": int(c[5]),
                "symbol": sym,
                "exchange": "NSE"
            })

        df = pl.DataFrame(records)
        # Parse timestamp string to Datetime
        df = df.with_columns(
            pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S%z", strict=False)
        )

        # Save to Silver Lakehouse
        interval_code = "1m" if interval == "ONE_MINUTE" else "5m"
        save_dir = settings.SILVER_DIR / f"ohlcv_{interval_code}" / "exchange=NSE" / f"symbol={sym}"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_file = save_dir / "data.parquet"
        df.write_parquet(save_file)
        
        logger.info(f"Saved {len(df)} candles to {save_file}")
        print(f"\n--- {sym} {interval} BARS (Top 5) ---")
        print(df.head(5))
        print(f"\n--- {sym} {interval} BARS (Latest 5) ---")
        print(df.tail(5))
        print("=" * 70)

if __name__ == "__main__":
    fetch_intraday_sample(["RELIANCE", "TCS"], interval="ONE_MINUTE")

