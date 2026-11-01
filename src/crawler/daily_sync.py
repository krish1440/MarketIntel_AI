import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import polars as pl
import yfinance as yf
from src.config.settings import settings

logger = logging.getLogger(__name__)

class DailySyncer:
    """
    Performs fast incremental daily synchronization:
    Checks the latest candle on disk and fetches only the missing days (delta),
    appending new rows to existing Parquet partitions without re-downloading history.
    """
    def __init__(self, exchange: str = "NSE"):
        self.exchange = exchange
        self.suffix = ".NS" if exchange == "NSE" else ".BO"
        self.base_dir = settings.SILVER_DIR / "ohlcv_1d" / f"exchange={exchange}"

    def sync_symbol(self, symbol: str) -> Tuple[str, bool, int, str]:
        """
        Synchronizes a single stock with the latest day's candle.
        Returns: (symbol, success, new_bars_count, message)
        """
        target_dir = self.base_dir / f"symbol={symbol}"
        target_file = target_dir / "data.parquet"

        if not target_file.exists():
            return (symbol, False, 0, "FILE_NOT_FOUND")

        try:
            # Read existing data
            existing_df = pl.read_parquet(target_file)
            if len(existing_df) == 0:
                return (symbol, False, 0, "EXISTING_EMPTY")

            last_date = existing_df["date"].max()
            last_date_str = str(last_date)[:10]

            # Dynamically calculate missing calendar days to prevent any gap
            today = date.today()
            if hasattr(last_date, "date"):
                last_d = last_date.date()
            elif isinstance(last_date, date):
                last_d = last_date
            else:
                last_d = datetime.strptime(last_date_str, "%Y-%m-%d").date()

            days_missing = (today - last_d).days
            if days_missing <= 0:
                return (symbol, True, 0, "ALREADY_UP_TO_DATE")

            # Dynamically request missing days (e.g. 5d, 10d, or date range)
            ticker_str = f"{symbol}{self.suffix}"
            ticker = yf.Ticker(ticker_str)
            if days_missing > 30:
                recent_hist = ticker.history(start=last_d.strftime("%Y-%m-%d"), auto_adjust=True)
            else:
                fetch_period = f"{max(5, days_missing + 3)}d"
                recent_hist = ticker.history(period=fetch_period, auto_adjust=True)

            if recent_hist.empty:
                return (symbol, True, 0, "ALREADY_UP_TO_DATE")

            recent_hist = recent_hist.reset_index()
            recent_hist.columns = [c.lower().replace(" ", "_") for c in recent_hist.columns]
            new_df = pl.from_pandas(recent_hist)

            cols_to_keep = ["date", "open", "high", "low", "close", "volume"]
            avail = [c for c in cols_to_keep if c in new_df.columns]
            new_df = new_df.select(avail)

            # Filter out invalid or incomplete rows
            new_df = new_df.filter(
                pl.col("open").is_not_null() &
                pl.col("close").is_not_null() &
                (pl.col("volume") >= 0)
            )

            # Filter for rows strictly newer than our last date
            # Ensure both date columns match timezone/format
            new_bars = new_df.filter(pl.col("date") > last_date)

            if len(new_bars) == 0:
                return (symbol, True, 0, "UP_TO_DATE")

            # Add metadata
            new_bars = new_bars.with_columns([
                pl.lit(symbol).alias("symbol"),
                pl.lit(self.exchange).alias("exchange")
            ])

            # Append to existing and save
            combined_df = pl.concat([existing_df, new_bars]).unique(subset=["date"]).sort("date")
            combined_df.write_parquet(target_file)

            return (symbol, True, len(new_bars), f"Appended {len(new_bars)} new day(s)")

        except Exception as e:
            return (symbol, False, 0, f"ERROR: {str(e)[:80]}")

    def sync_bulk(self, symbols: List[str], max_workers: int = 12) -> Tuple[int, int]:
        """
        Fast multi-threaded incremental sync across all stocks.
        """
        total = len(symbols)
        logger.info(f"Starting Daily Incremental Sync for {total} stocks with {max_workers} threads...")
        
        updated_count = 0
        up_to_date_count = 0
        error_count = 0
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {executor.submit(self.sync_symbol, sym): sym for sym in symbols}
            for future in as_completed(future_to_sym):
                completed += 1
                sym, success, count, msg = future.result()
                
                if success:
                    if count > 0:
                        updated_count += 1
                    else:
                        up_to_date_count += 1
                else:
                    error_count += 1

                if completed % 500 == 0 or completed == total:
                    logger.info(f"--> Sync Progress: {completed}/{total} | {updated_count} updated | {up_to_date_count} already current")

        logger.info(f"Daily Sync Complete: {updated_count} updated, {up_to_date_count} up-to-date, {error_count} errors.")
        return updated_count, up_to_date_count

