import time
import logging
from datetime import datetime, date, timedelta, time as dtime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import polars as pl

from src.config.settings import settings
from src.broker.angel_client import AngelClient
from src.master.security_master import SecurityMaster

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

class IntradayGapSyncer:
    """
    Institutional 1-Minute Historical Candle Gap Syncer:
    - Inspects the latest 1-minute candle on disk (Silver Parquet).
    - Detects missing days/hours between last recorded bar and latest market close.
    - Uses Angel One SmartAPI getCandleData to fetch missing 1-minute intervals.
    - Atomically merges, deduplicates by timestamp, sorts chronologically, and updates Silver 1m & 5m.
    """

    def __init__(self, angel_client: Optional[AngelClient] = None, exchange: str = "NSE"):
        self.exchange = exchange
        self.angel = angel_client or AngelClient()
        self.sec_master = SecurityMaster()
        self.silver_1m_base = settings.SILVER_DIR / "ohlcv_1m" / f"exchange={exchange}"
        self.silver_5m_base = settings.SILVER_DIR / "ohlcv_5m" / f"exchange={exchange}"
        self.silver_1m_base.mkdir(parents=True, exist_ok=True)
        self.silver_5m_base.mkdir(parents=True, exist_ok=True)
        self.min_req_interval = 1.5  # Safe rate limit: 1.5s interval ensures zero SmartAPI rate limits
        self.last_req_time = 0.0

    def _rate_limit(self):
        """Enforces safe API rate limit to prevent SmartAPI 429 errors."""
        elapsed = time.time() - self.last_req_time
        if elapsed < self.min_req_interval:
            time.sleep(self.min_req_interval - elapsed)
        self.last_req_time = time.time()

    def detect_gap(self, symbol: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Determines if there is a gap between the last 1-minute candle on disk
        and the latest completed trading period.
        Returns: (from_datetime, to_datetime) if gap exists, or None if up to date.
        """
        target_file = self.silver_1m_base / f"symbol={symbol}" / "data.parquet"
        now_ist = datetime.now(IST)

        # Target end date: If market is currently open, we backfill up to today 09:15 AM
        # If market is closed, we backfill up to the most recent trading day 15:30 IST
        market_open_today = datetime.combine(now_ist.date(), dtime(9, 15), tzinfo=IST)
        market_close_today = datetime.combine(now_ist.date(), dtime(15, 30), tzinfo=IST)

        if now_ist.weekday() >= 5: # Weekend (Saturday/Sunday)
            days_back = now_ist.weekday() - 4
            target_to_date = (now_ist - timedelta(days=days_back)).replace(
                hour=15, minute=30, second=0, microsecond=0
            )
        elif now_ist.time() < dtime(9, 15): # Pre-market
            days_back = 3 if now_ist.weekday() == 0 else 1
            target_to_date = (now_ist - timedelta(days=days_back)).replace(
                hour=15, minute=30, second=0, microsecond=0
            )
        elif dtime(9, 15) <= now_ist.time() < dtime(15, 30): # Market is open
            target_to_date = market_open_today
        else: # Post market (after 15:30)
            target_to_date = market_close_today

        if not target_file.exists():
            from_dt = (target_to_date - timedelta(days=7)).replace(hour=9, minute=15, second=0, microsecond=0)
            return (from_dt, target_to_date)

        try:
            # Check last timestamp on disk
            df = pl.read_parquet(target_file, columns=["timestamp"])
            if len(df) == 0:
                from_dt = (target_to_date - timedelta(days=7)).replace(hour=9, minute=15, second=0, microsecond=0)
                return (from_dt, target_to_date)

            last_ts = df["timestamp"].max()
            if isinstance(last_ts, str):
                last_dt = datetime.fromisoformat(last_ts)
            else:
                last_dt = last_ts

            if last_dt.tzinfo is not None:
                last_dt = last_dt.astimezone(IST)
            else:
                last_dt = last_dt.replace(tzinfo=IST)

            # If last candle is within 30 minutes of target, we consider it up to date
            if (target_to_date - last_dt).total_seconds() <= 1800:
                return None

            from_dt = last_dt + timedelta(minutes=1)
            # Normalize to market hours
            if from_dt.time() < dtime(9, 15):
                from_dt = from_dt.replace(hour=9, minute=15, second=0, microsecond=0)
            elif from_dt.time() > dtime(15, 25):
                # If after 15:25, roll to the next morning 09:15
                from_dt = (from_dt + timedelta(days=1)).replace(hour=9, minute=15, second=0, microsecond=0)

            # Skip weekend days for from_dt
            while from_dt.weekday() >= 5: # Saturday or Sunday
                from_dt = (from_dt + timedelta(days=1)).replace(hour=9, minute=15, second=0, microsecond=0)

            if from_dt >= target_to_date:
                return None

            return (from_dt, target_to_date)
        except Exception as e:
            logger.warning(f"Error checking 1m gap for {symbol}: {e}")
            return None

    def sync_symbol(self, symbol: str) -> Tuple[str, bool, int, str]:
        """
        Synchronizes missing 1-minute candles for a single stock.
        Returns: (symbol, success, new_bars_count, message)
        """
        gap = self.detect_gap(symbol)
        if not gap:
            return (symbol, True, 0, "ALREADY_UP_TO_DATE")

        from_dt, to_dt = gap
        token = self.sec_master.get_token(symbol, exchange=self.exchange)
        if not token:
            return (symbol, False, 0, "TOKEN_NOT_FOUND")

        from_str = from_dt.strftime("%Y-%m-%d %H:%M")
        to_str = to_dt.strftime("%Y-%m-%d %H:%M")

        self._rate_limit()

        try:
            raw_data = self.angel.get_historical_candles(
                exchange=self.exchange,
                symbol_token=str(token),
                interval="ONE_MINUTE",
                from_date=from_str,
                to_date=to_str
            )

            if not raw_data:
                return (symbol, True, 0, "NO_NEW_DATA_ON_SERVER")

            new_candles = []
            for c in raw_data:
                new_candles.append({
                    "timestamp": c[0],
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": int(c[5]),
                    "symbol": symbol,
                    "exchange": self.exchange
                })

            new_df = pl.DataFrame(new_candles)
            new_df = new_df.with_columns(
                pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S%z", strict=False).dt.convert_time_zone("UTC")
            ).drop_nulls()

            target_file = self.silver_1m_base / f"symbol={symbol}" / "data.parquet"
            target_dir = target_file.parent
            target_dir.mkdir(parents=True, exist_ok=True)

            if target_file.exists():
                existing_df = pl.read_parquet(target_file)
                combined = pl.concat([existing_df, new_df]).unique(subset=["timestamp"]).sort("timestamp")
            else:
                combined = new_df.unique(subset=["timestamp"]).sort("timestamp")

            # Write updated 1m Parquet
            temp_file = target_file.with_suffix(".tmp")
            combined.write_parquet(temp_file)
            temp_file.replace(target_file)

            # Resample to 5m Parquet
            self._resample_to_5m(combined, symbol)

            return (symbol, True, len(new_df), f"Added {len(new_df)} missing 1m bars ({from_str} to {to_str})")

        except Exception as e:
            return (symbol, False, 0, f"SYNC_ERROR: {str(e)}")

    def _resample_to_5m(self, df_1m: pl.DataFrame, symbol: str):
        """Vectorized on-the-fly resampling from 1m to 5m in Polars."""
        if len(df_1m) == 0:
            return
        dir_5m = self.silver_5m_base / f"symbol={symbol}"
        dir_5m.mkdir(parents=True, exist_ok=True)
        file_5m = dir_5m / "data.parquet"

        df_5m = (
            df_1m.group_by_dynamic("timestamp", every="5m")
            .agg([
                pl.col("open").first(),
                pl.col("high").max(),
                pl.col("low").min(),
                pl.col("close").last(),
                pl.col("volume").sum(),
                pl.lit(symbol).alias("symbol"),
                pl.lit(self.exchange).alias("exchange")
            ])
            .drop_nulls()
        )
        temp_5m = file_5m.with_suffix(".tmp")
        df_5m.write_parquet(temp_5m)
        temp_5m.replace(file_5m)

