import sys
import logging
from pathlib import Path
import polars as pl
import yfinance as yf

# Ensure UTF-8 output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("GlobalMacro")

GLOBAL_TICKERS = {
    "SP500": "^GSPC",          # US S&P 500 (Global Market Anchor)
    "NASDAQ100": "^IXIC",      # US Nasdaq Composite (Leads Indian IT / Tech)
    "CRUDE_OIL": "CL=F",       # WTI Crude Oil (Margin indicator for Paints, Oil, Chem)
    "USD_INR": "INR=X",        # US Dollar vs Indian Rupee Currency Rate
    "US10Y_YIELD": "^TNX",     # US 10-Year Treasury Yield (Global Risk-On/Off)
}

def fetch_global_correlators():
    bronze_base = settings.BRONZE_DIR / "macro" / "global"
    silver_base = settings.SILVER_DIR / "macro" / "global"
    bronze_base.mkdir(parents=True, exist_ok=True)
    silver_base.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("FETCHING 5 GLOBAL MACRO CORRELATORS (INCEPTION TO DATE)")
    logger.info("=" * 70)

    results = {}
    for name, ticker_str in GLOBAL_TICKERS.items():
        silver_dir = silver_base / f"ticker={name}"
        silver_file = silver_dir / "data.parquet"
        bronze_file = bronze_base / f"raw_{name}.parquet"

        try:
            ticker = yf.Ticker(ticker_str)
            try:
                hist = ticker.history(period="max", auto_adjust=True)
            except Exception:
                hist = ticker.history(period="20y", auto_adjust=True)

            if hist.empty or len(hist) < 5:
                hist = ticker.history(period="10y", auto_adjust=True)
                if hist.empty or len(hist) < 5:
                    logger.warning(f"--> {name:15} | FAILED: EMPTY")
                    continue

            hist = hist.reset_index()
            hist.columns = [c.lower().replace(" ", "_") for c in hist.columns]
            raw_pl = pl.from_pandas(hist)

            # Save raw to Bronze
            raw_pl.write_parquet(bronze_file)

            # Clean and standardize for Silver
            cols = ["date", "open", "high", "low", "close", "volume"]
            avail = [c for c in cols if c in raw_pl.columns]
            clean_pl = raw_pl.select(avail).filter(
                pl.col("open").is_not_null() &
                pl.col("close").is_not_null()
            ).with_columns([
                pl.lit(name).alias("global_ticker"),
                pl.lit(ticker_str).alias("symbol")
            ])

            silver_dir.mkdir(parents=True, exist_ok=True)
            clean_pl.write_parquet(silver_file)
            
            d_min = str(clean_pl["date"].min())[:10]
            d_max = str(clean_pl["date"].max())[:10]
            logger.info(f"--> {name:15} ({ticker_str:8}) | {len(clean_pl):5} bars | {d_min} to {d_max}")
            results[name] = len(clean_pl)

        except Exception as e:
            logger.error(f"Error fetching {name}: {e}")

    logger.info("=" * 70)
    logger.info(f"GLOBAL MACRO CORRELATORS COMPLETE: {len(results)}/5 STORED ON DISK!")
    logger.info(f"Silver Location: {silver_base}")
    logger.info("=" * 70)

if __name__ == "__main__":
    fetch_global_correlators()

