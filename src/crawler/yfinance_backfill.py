import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import polars as pl
import yfinance as yf
from src.config.settings import settings

logger = logging.getLogger(__name__)

class YFinanceBackfiller:
    """
    Downloads multi-decade (inception-to-present, period='max') adjusted daily OHLCV bars
    for NSE/BSE securities and stores them into the Silver Lakehouse layer in partitioned Parquet format.
    Supports resuming, skipping existing files, and clean null filtering.
    """
    def __init__(self, exchange: str = "NSE"):
        self.exchange = exchange
        self.suffix = ".NS" if exchange == "NSE" else ".BO"
        self.output_base = settings.SILVER_DIR / "ohlcv_1d" / f"exchange={exchange}"
        self.output_base.mkdir(parents=True, exist_ok=True)

    def backfill_symbol(self, symbol: str, period: str = "max", overwrite: bool = False) -> Tuple[str, bool, int, str]:
        """
        Backfills a single symbol from inception to date (period='max').
        Returns: (symbol, success_bool, bar_count, message)
        """
        ticker_str = f"{symbol}{self.suffix}"
        target_dir = self.output_base / f"symbol={symbol}"
        target_parquet = target_dir / "data.parquet"

        # Resume check: if already exists and overwrite is False, skip
        if target_parquet.exists() and not overwrite:
            try:
                existing_df = pl.read_parquet(target_parquet)
                if len(existing_df) > 10:
                    return (symbol, True, len(existing_df), "SKIPPED_ALREADY_EXISTS")
            except Exception:
                pass  # Corrupt file, re-download

        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            ticker = yf.Ticker(ticker_str)
            hist = ticker.history(period=period, auto_adjust=True)
            
            if hist.empty or len(hist) < 3:
                return (symbol, False, 0, "EMPTY_OR_NOT_FOUND")

            # Clean and standardize
            hist = hist.reset_index()
            hist.columns = [c.lower().replace(" ", "_") for c in hist.columns]
            
            df = pl.from_pandas(hist)
            
            # Keep standard columns
            standard_cols = ["date", "open", "high", "low", "close", "volume"]
            available = [c for c in standard_cols if c in df.columns]
            df = df.select(available)
            
            # Filter out null / invalid bars
            df = df.filter(
                pl.col("open").is_not_null() &
                pl.col("close").is_not_null() &
                (pl.col("volume") >= 0)
            )

            if len(df) == 0:
                return (symbol, False, 0, "NO_VALID_BARS")

            # Add symbol & exchange tags
            df = df.with_columns([
                pl.lit(symbol).alias("symbol"),
                pl.lit(self.exchange).alias("exchange")
            ])
            
            # Save to Parquet
            df.write_parquet(target_parquet)
            date_min = str(df["date"].min())[:10]
            date_max = str(df["date"].max())[:10]
            return (symbol, True, len(df), f"{date_min} to {date_max}")

        except Exception as e:
            return (symbol, False, 0, f"ERROR: {str(e)[:100]}")

    def backfill_bulk(
        self,
        symbols: List[str],
        max_workers: int = 8,
        period: str = "max",
        overwrite: bool = False
    ) -> Tuple[int, int]:
        """
        Multi-threaded bulk downloader for inception-to-date data.
        Returns: (success_count, skipped_count)
        """
        total = len(symbols)
        logger.info(f"Starting Inception-to-Date ('{period}') download for {total} symbols with {max_workers} threads...")
        
        success_count = 0
        skipped_count = 0
        failed_count = 0
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {
                executor.submit(self.backfill_symbol, sym, period, overwrite): sym
                for sym in symbols
            }
            
            for future in as_completed(future_to_sym):
                completed += 1
                sym, success, count, msg = future.result()
                
                if success:
                    if "SKIPPED" in msg:
                        skipped_count += 1
                    else:
                        success_count += 1
                        logger.info(f"[{completed}/{total}] {sym:12} | {count:5} bars saved | {msg}")
                else:
                    failed_count += 1
                    logger.debug(f"[{completed}/{total}] {sym:12} | FAILED: {msg}")

                if completed % 100 == 0:
                    logger.info(f"--> Progress: {completed}/{total} processed ({success_count} downloaded, {skipped_count} skipped, {failed_count} failed)")

        logger.info(f"Bulk download finished: {success_count} downloaded, {skipped_count} skipped, {failed_count} failed out of {total} total.")
        return success_count, skipped_count
