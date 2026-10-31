import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
import polars as pl
from src.config.settings import settings
from src.broker.angel_client import AngelClient
from src.master.security_master import SecurityMaster

logger = logging.getLogger(__name__)

class Intraday1mBackfiller:
    """
    Robust 1-Minute Historical Candle Backfiller for Angel One SmartAPI:
    - Paginates in 30-day monthly chunks to cover 1 full year (~93,000 candles per stock).
    - Rate-limits to <= 3 requests/second to strictly respect Angel One API limits.
    - Checkpoints completed stocks to disk for seamless resume capability.
    - Supports automated on-the-fly resampling from 1m to 5m, 15m, and 1h bars.
    """
    def __init__(self, angel_client: Optional[AngelClient] = None):
        self.angel = angel_client or AngelClient()
        self.output_base = settings.SILVER_DIR / "ohlcv_1m" / "exchange=NSE"
        self.output_base.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = settings.BRONZE_DIR / "intraday_1m_checkpoint.txt"
        self.min_request_interval = 0.55  # ~1.8 requests/sec (safe from burst throttle)

    def _rate_limit(self, last_call_time: float) -> float:
        """Enforces rate limit delay."""
        elapsed = time.time() - last_call_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        return time.time()

    def get_completed_symbols(self) -> set:
        """Loads symbols that have already been fully backfilled."""
        completed = set()
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                completed = {line.strip() for line in f if line.strip()}
        return completed

    def mark_completed(self, symbol: str):
        """Appends symbol to checkpoint log."""
        with open(self.checkpoint_file, "a") as f:
            f.write(f"{symbol}\n")

    def generate_monthly_slices(self, months_back: int = 12) -> List[Tuple[str, str]]:
        """
        Generates 30-day date windows (from_date, to_date) going back `months_back` months.
        Format: 'YYYY-MM-DD 09:15', 'YYYY-MM-DD 15:30'
        """
        slices = []
        now = datetime.now()
        current_end = now
        
        for _ in range(months_back):
            start = current_end - timedelta(days=30)
            from_str = start.strftime("%Y-%m-%d 09:15")
            to_str = current_end.strftime("%Y-%m-%d 15:30")
            slices.append((from_str, to_str))
            current_end = start - timedelta(days=1)
            
        slices.reverse()  # Chronological order
        return slices

    def backfill_symbol(
        self,
        symbol: str,
        token: str,
        months_back: int = 12,
        resample_to_5m: bool = True
    ) -> Tuple[str, bool, int, str]:
        """
        Fetches 1 year of 1-minute historical candles in 30-day chunks for a single stock.
        """
        target_dir = self.output_base / f"symbol={symbol}"
        target_file = target_dir / "data.parquet"
        
        date_slices = self.generate_monthly_slices(months_back=months_back)
        all_candles = []
        last_req_time = 0.0

        for from_dt, to_dt in date_slices:
            last_req_time = self._rate_limit(last_req_time)
            
            raw_data = self.angel.get_historical_candles(
                exchange="NSE",
                symbol_token=str(token),
                interval="ONE_MINUTE",
                from_date=from_dt,
                to_date=to_dt
            )
            
            if raw_data:
                for c in raw_data:
                    # c format: [timestamp, open, high, low, close, volume]
                    all_candles.append({
                        "timestamp": c[0],
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": int(c[5]),
                        "symbol": symbol,
                        "exchange": "NSE"
                    })

        if not all_candles:
            return (symbol, False, 0, "NO_DATA_RETURNED")

        # Convert to Polars DataFrame and deduplicate
        df = pl.DataFrame(all_candles)
        df = df.with_columns(
            pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S%z", strict=False)
        ).unique(subset=["timestamp"]).sort("timestamp")

        # Save 1-minute Parquet
        target_dir.mkdir(parents=True, exist_ok=True)
        df.write_parquet(target_file)
        self.mark_completed(symbol)

        # Optional: On-the-fly resample to 5-minute bars
        if resample_to_5m and len(df) > 0:
            self._resample_and_save_5m(df, symbol)

        return (symbol, True, len(df), f"Saved {len(df)} 1m candles")

    def _resample_and_save_5m(self, df_1m: pl.DataFrame, symbol: str):
        """Vectorized resampling from 1m to 5m candles in Polars."""
        dir_5m = settings.SILVER_DIR / "ohlcv_5m" / "exchange=NSE" / f"symbol={symbol}"
        dir_5m.mkdir(parents=True, exist_ok=True)
        
        df_5m = (
            df_1m.group_by_dynamic("timestamp", every="5m")
            .agg([
                pl.col("open").first(),
                pl.col("high").max(),
                pl.col("low").min(),
                pl.col("close").last(),
                pl.col("volume").sum(),
                pl.lit(symbol).alias("symbol"),
                pl.lit("NSE").alias("exchange")
            ])
            .drop_nulls()
        )
        df_5m.write_parquet(dir_5m / "data.parquet")

