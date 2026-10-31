import logging
from pathlib import Path
from typing import Dict, List, Tuple
import polars as pl
import yfinance as yf
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Complete list of 16 official NSE Sectoral/Thematic indices + India VIX + Benchmarks
NSE_MACRO_INDICES: Dict[str, str] = {
    # Volatility / Market Fear
    "INDIA_VIX": "^INDIAVIX",
    
    # Core Benchmarks
    "NIFTY_50": "^NSEI",
    "NIFTY_BANK": "^NSEBANK",
    "NIFTY_MIDCAP_150": "NIFTY_MIDCAP_150.NS",
    "NIFTY_SMALLCAP_250": "NIFTY_SMALL_250.NS",
    
    # Sectoral Indices
    "NIFTY_IT": "^CNXIT",
    "NIFTY_AUTO": "^CNXAUTO",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "NIFTY_FMCG": "^CNXFMCG",
    "NIFTY_METAL": "^CNXMETAL",
    "NIFTY_ENERGY": "^CNXENERGY",
    "NIFTY_REALTY": "^CNXREALTY",
    "NIFTY_INFRA": "^CNXINFRA",
    "NIFTY_FIN_SERVICE": "NIFTY_FIN_SERVICE.NS",
    "NIFTY_PSU_BANK": "^CNXPSUBANK",
    "NIFTY_MEDIA": "^CNXMEDIA",
    "NIFTY_COMMODITIES": "^CNXCOMMODITIES",
    "NIFTY_CONSUMER_DURABLES": "NIFTY_CONSR_DURBL.NS",
    "NIFTY_PSE": "^CNXPSE",
    "NIFTY_SERVICES": "^CNXSERVICE",
}

class MacroIndicesBackfiller:
    """
    Downloads full historical daily data for all 16 official NSE sectors,
    the Nifty benchmarks, and India VIX from inception to present day.
    Saves raw files to Bronze and cleaned, standardized files to Silver Lakehouse.
    """
    def __init__(self):
        self.bronze_dir = settings.BRONZE_DIR / "macro"
        self.silver_dir = settings.SILVER_DIR / "macro"
        self.bronze_dir.mkdir(parents=True, exist_ok=True)
        self.silver_dir.mkdir(parents=True, exist_ok=True)

    def backfill_index(self, name: str, ticker_symbol: str) -> Tuple[str, bool, int, str]:
        """Downloads a single index from inception to present."""
        silver_index_dir = self.silver_dir / f"index={name}"
        silver_file = silver_index_dir / "data.parquet"
        bronze_file = self.bronze_dir / f"raw_{name}.parquet"

        try:
            ticker = yf.Ticker(ticker_symbol)
            try:
                hist = ticker.history(period="max", auto_adjust=True)
            except Exception:
                hist = ticker.history(period="10y", auto_adjust=True)

            if hist.empty or len(hist) < 5:
                # Try 5y
                hist = ticker.history(period="5y", auto_adjust=True)
                if hist.empty or len(hist) < 5:
                    return (name, False, 0, "EMPTY_DATA")

            hist = hist.reset_index()
            hist.columns = [c.lower().replace(" ", "_") for c in hist.columns]
            
            raw_pl = pl.from_pandas(hist)
            # Save raw copy to Bronze
            raw_pl.write_parquet(bronze_file)

            # Clean and standardize for Silver
            cols = ["date", "open", "high", "low", "close", "volume"]
            avail = [c for c in cols if c in raw_pl.columns]
            clean_pl = raw_pl.select(avail).filter(
                pl.col("open").is_not_null() &
                pl.col("close").is_not_null()
            ).with_columns([
                pl.lit(name).alias("index_name"),
                pl.lit(ticker_symbol).alias("ticker")
            ])

            silver_index_dir.mkdir(parents=True, exist_ok=True)
            clean_pl.write_parquet(silver_file)
            
            date_min = str(clean_pl["date"].min())[:10]
            date_max = str(clean_pl["date"].max())[:10]
            return (name, True, len(clean_pl), f"{date_min} to {date_max}")

        except Exception as e:
            return (name, False, 0, f"ERROR: {str(e)[:80]}")

    def backfill_all(self) -> Dict[str, Tuple[bool, int, str]]:
        """Downloads all sectors, benchmarks, and India VIX."""
        logger.info(f"Starting Macro & Sector Indices Backfill ({len(NSE_MACRO_INDICES)} total indices)...")
        results = {}

        for name, ticker in NSE_MACRO_INDICES.items():
            name, success, count, msg = self.backfill_index(name, ticker)
            results[name] = (success, count, msg)
            if success:
                logger.info(f"--> {name:24} | {count:5} bars | {msg}")
            else:
                logger.warning(f"--> {name:24} | FAILED: {msg}")

        logger.info(f"Macro & Sector Backfill Complete: {sum(1 for s, _, _ in results.values() if s)}/{len(NSE_MACRO_INDICES)} successful.")
        return results

