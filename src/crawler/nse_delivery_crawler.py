import logging
import io
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional
import requests
import polars as pl
from src.config.settings import settings

logger = logging.getLogger(__name__)

class NseDeliveryCrawler:
    """
    Crawls official NSE Security-wise Delivery Position Bhavcopies:
    Extracts: SYMBOL, SERIES, TRADED_QTY, DELIV_QTY, DELIV_PER (Delivery %)
    Saves raw daily CSVs to Bronze and unified delivery tables to Silver Lakehouse.
    """
    BHAVDATA_URL_TEMPLATE = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{day}{month}{year}.csv"

    def __init__(self):
        self.bronze_dir = settings.BRONZE_DIR / "delivery"
        self.silver_dir = settings.SILVER_DIR / "delivery"
        self.bronze_dir.mkdir(parents=True, exist_ok=True)
        self.silver_dir.mkdir(parents=True, exist_ok=True)
        self.master_delivery_file = self.silver_dir / "delivery_history.parquet"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_daily_delivery_bhavcopy(self, target_date: date) -> Optional[pl.DataFrame]:
        """
        Fetches official NSE delivery report for a single trading date.
        Date format in URL: DDMMYYYY (e.g. 30102024)
        """
        day_str = target_date.strftime("%d")
        month_str = target_date.strftime("%m")
        year_str = target_date.strftime("%Y")
        url = self.BHAVDATA_URL_TEMPLATE.format(day=day_str, month=month_str, year=year_str)

        bronze_file = self.bronze_dir / f"sec_bhav_{year_str}{month_str}{day_str}.parquet"
        if bronze_file.exists():
            try:
                return pl.read_parquet(bronze_file)
            except Exception:
                pass

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 1000:
                raw_df = pl.read_csv(io.BytesIO(resp.content))
                # Strip column spaces
                raw_df = raw_df.rename({c: c.strip() for c in raw_df.columns})
                
                # Filter for EQ series (cash equity)
                if "SERIES" in raw_df.columns:
                    raw_df = raw_df.filter(pl.col("SERIES") == "EQ")

                # Keep vital delivery columns
                rename_map = {
                    "SYMBOL": "symbol",
                    "DATE1": "date_str",
                    "TTL_TRD_QNTY": "traded_qty",
                    "DELIV_QTY": "delivery_qty",
                    "DELIV_PER": "delivery_pct"
                }
                avail = {k: v for k, v in rename_map.items() if k in raw_df.columns}
                clean_df = raw_df.rename(avail).select(list(avail.values()))

                # Cast numeric types safely
                clean_df = clean_df.with_columns([
                    pl.col("traded_qty").cast(pl.Int64, strict=False),
                    pl.col("delivery_qty").cast(pl.Int64, strict=False),
                    pl.col("delivery_pct").cast(pl.Float32, strict=False),
                    pl.lit(target_date).cast(pl.Date).alias("date")
                ])
                if "date_str" in clean_df.columns:
                    clean_df = clean_df.drop("date_str")

                # Save raw daily file to Bronze
                clean_df.write_parquet(bronze_file)
                logger.info(f"Saved delivery bhavcopy for {target_date} ({len(clean_df)} equities).")
                return clean_df
            else:
                return None
        except Exception as e:
            logger.debug(f"Could not fetch delivery for {target_date}: {e}")
            return None

    def crawl_recent_delivery_history(self, days_back: int = 30) -> pl.DataFrame:
        """
        Crawls recent daily delivery bhavcopies and builds the compiled delivery table.
        """
        logger.info(f"Crawling NSE delivery reports for past {days_back} trading days...")
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        daily_dfs = []
        curr = start_date
        while curr <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if curr.weekday() < 5:
                df = self.fetch_daily_delivery_bhavcopy(curr)
                if df is not None and len(df) > 0:
                    daily_dfs.append(df)
                time.sleep(0.3)  # Gentle delay to respect NSE rate limits
            curr += timedelta(days=1)

        if daily_dfs:
            combined = pl.concat(daily_dfs).unique(subset=["date", "symbol"]).sort(["date", "symbol"])
            combined.write_parquet(self.master_delivery_file)
            logger.info(f"Compiled {len(combined)} delivery records into {self.master_delivery_file}")
            return combined
        else:
            logger.warning("No new delivery bhavcopies fetched.")
            if self.master_delivery_file.exists():
                return pl.read_parquet(self.master_delivery_file)
            return pl.DataFrame()

