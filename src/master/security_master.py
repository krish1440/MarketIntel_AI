import logging
import polars as pl
import requests
from pathlib import Path
from typing import Optional, List, Dict
from src.config.settings import settings

logger = logging.getLogger(__name__)

class SecurityMaster:
    """
    Manages Dual-Exchange (NSE & BSE) security normalization using ISIN as the golden primary key.
    Stores and queries the Master Security Table in Bronze Parquet format.
    """
    NSE_EQUITY_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    MASTER_PARQUET_PATH = settings.BRONZE_DIR / "master" / "securities_master.parquet"

    def __init__(self):
        self.df: Optional[pl.DataFrame] = None
        if self.MASTER_PARQUET_PATH.exists():
            try:
                self.df = pl.read_parquet(self.MASTER_PARQUET_PATH)
                logger.info(f"Loaded existing securities master: {len(self.df)} records.")
            except Exception as e:
                logger.warning(f"Could not load existing securities master: {e}")

    def build_master_universe(self, angel_instruments: Optional[List[Dict]] = None) -> pl.DataFrame:
        """
        Builds the unified master universe combining:
        1. Angel One complete instrument dump (tokens, exchange, symbols)
        2. NSE Official Equity list (ISIN, Company Name, Face Value, Listing Date)
        Saves result to bronze/master/securities_master.parquet.
        """
        logger.info("Building unified Master Security Universe...")
        
        # 1. Fetch NSE Official Equity List
        nse_df = None
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(self.NSE_EQUITY_LIST_URL, headers=headers, timeout=15)
            if r.status_code == 200:
                import io
                nse_df = pl.read_csv(io.BytesIO(r.content))
                # Strip leading/trailing whitespaces from column headers
                nse_df = nse_df.rename({c: c.strip() for c in nse_df.columns})
                
                # Standardize columns: SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
                rename_map = {
                    "SYMBOL": "nse_symbol",
                    "NAME OF COMPANY": "company_name",
                    "SERIES": "series",
                    "ISIN NUMBER": "isin",
                    "FACE VALUE": "face_value"
                }
                valid_renames = {k: v for k, v in rename_map.items() if k in nse_df.columns}
                nse_df = nse_df.rename(valid_renames)
                if "series" in nse_df.columns:
                    nse_df = nse_df.filter(pl.col("series") == "EQ")
                logger.info(f"Fetched {len(nse_df)} official NSE EQ stocks.")
        except Exception as e:
            logger.warning(f"Could not fetch official NSE EQUITY_L.csv: {e}")

        # 2. Process Angel One Instruments if available
        instruments_df = None
        if angel_instruments:
            raw_pl = pl.DataFrame(angel_instruments)
            # Filter for NSE and BSE cash equities
            # Angel columns: token, symbol, name, expiry, strike, lotsize, instrumenttype, exch_seg, tick_size
            equities = raw_pl.filter(
                (pl.col("exch_seg").is_in(["NSE", "BSE"])) &
                (pl.col("symbol").str.ends_with("-EQ") | (pl.col("exch_seg") == "BSE"))
            )
            instruments_df = equities
            logger.info(f"Filtered {len(instruments_df)} cash equity instruments from Angel One dump.")

        # 3. Create unified schema
        if nse_df is not None:
            unified = nse_df.select([
                pl.col("isin"),
                pl.col("nse_symbol"),
                pl.col("company_name"),
                pl.lit("NSE").alias("primary_exchange"),
                pl.lit(True).alias("is_active")
            ])
            
            # Map BSE tokens and codes if instruments_df is available
            if instruments_df is not None:
                # Extract Angel NSE tokens
                nse_tokens = instruments_df.filter(pl.col("exch_seg") == "NSE").select([
                    pl.col("symbol").str.replace("-EQ", "").alias("nse_symbol"),
                    pl.col("token").alias("nse_token")
                ]).unique(subset=["nse_symbol"])
                
                unified = unified.join(nse_tokens, on="nse_symbol", how="left")
                
                # Extract BSE tokens
                bse_tokens = instruments_df.filter(pl.col("exch_seg") == "BSE").select([
                    pl.col("name").alias("bse_name"),
                    pl.col("token").alias("bse_code"),
                    pl.col("symbol").alias("bse_symbol")
                ]).unique(subset=["bse_name"])
                
                # Merge BSE code where company names or symbols match
                unified = unified.join(
                    bse_tokens,
                    left_on="nse_symbol",
                    right_on="bse_name",
                    how="left"
                )
            else:
                unified = unified.with_columns([
                    pl.lit(None).cast(pl.Utf8).alias("bse_code"),
                    pl.lit(None).cast(pl.Utf8).alias("nse_token")
                ])
        elif instruments_df is not None:
            # Fallback if NSE CSV failed: build directly from Angel instruments
            unified = instruments_df.select([
                pl.col("name").alias("company_name"),
                pl.col("symbol").alias("nse_symbol"),
                pl.col("token").alias("nse_token"),
                pl.lit(None).cast(pl.Utf8).alias("isin"),
                pl.lit("NSE").alias("primary_exchange"),
                pl.lit(True).alias("is_active")
            ])
        else:
            raise RuntimeError("Neither NSE Equity list nor Angel instruments could be loaded.")

        # Save to Parquet
        self.MASTER_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
        unified.write_parquet(self.MASTER_PARQUET_PATH)
        self.df = unified
        logger.info(f"Saved master universe with {len(unified)} securities to {self.MASTER_PARQUET_PATH}")
        return unified

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search securities by symbol or company name."""
        if self.df is None:
            return []
        
        q = query.upper()
        matches = self.df.filter(
            pl.col("nse_symbol").str.to_uppercase().str.contains(q) |
            pl.col("company_name").str.to_uppercase().str.contains(q)
        ).head(limit)
        
        return matches.to_dicts()

    def get_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Lookup security by exact NSE symbol."""
        if self.df is None:
            return None
        res = self.df.filter(pl.col("nse_symbol") == symbol.upper())
        if len(res) > 0:
            return res.to_dicts()[0]
        return None

