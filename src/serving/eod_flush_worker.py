import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import polars as pl
from src.config.settings import settings
from src.serving.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class EODFlushWorker:
    """
    Asynchronous Write-Behind Worker.
    Flushes completed in-memory candles from RAM into the permanent Silver Lakehouse
    at market close (03:45 PM IST), preventing data loss and freeing RAM.
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.redis = redis_mgr or RedisManager()
        self.silver_ohlcv_1m_base = settings.SILVER_DIR / "ohlcv_1m" / "exchange=NSE"
        self.silver_ohlcv_1m_base.mkdir(parents=True, exist_ok=True)

    def flush_symbol(self, exchange: str, symbol: str) -> int:
        """Flushes today's RAM candles for a single symbol to Parquet."""
        candles = self.redis.get_recent_candles(exchange, symbol, "1m", limit=500)
        if not candles:
            return 0

        target_dir = self.silver_ohlcv_1m_base / f"symbol={symbol}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "data.parquet"

        # Format RAM candles into Polars DataFrame (using 'timestamp' to match 1m schema)
        records = []
        for c in candles:
            records.append({
                "timestamp": datetime.fromtimestamp(float(c["timestamp"])),
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": int(c["volume"]),
                "symbol": symbol,
                "exchange": exchange
            })

        new_df = pl.DataFrame(records)

        # Merge with existing file if it exists, eliminating duplicates
        if target_file.exists():
            existing_df = pl.read_parquet(target_file)
            time_col = "timestamp" if "timestamp" in existing_df.columns else "date"
            if time_col != "timestamp":
                new_df = new_df.rename({"timestamp": time_col})
            # Cast datetime to match existing schema timezone
            new_df = new_df.with_columns(pl.col(time_col).cast(existing_df.schema[time_col]))
            merged_df = pl.concat([existing_df, new_df]).unique(subset=[time_col]).sort(time_col)
        else:
            merged_df = new_df.sort("timestamp")

        merged_df.write_parquet(target_file, compression="zstd")

        # Automatically Resample 1M to 5M Silver Lakehouse
        try:
            self._resample_to_5m(merged_df, symbol, exchange)
        except Exception as e:
            logger.warning(f"Could not auto-resample 5m for {symbol}: {e}")

        return len(new_df)

    def _resample_to_5m(self, df_1m: pl.DataFrame, symbol: str, exchange: str = "NSE"):
        """Vectorized on-the-fly resampling from 1m to 5m in Polars."""
        if len(df_1m) == 0:
            return
        dir_5m = settings.SILVER_DIR / "ohlcv_5m" / f"exchange={exchange}" / f"symbol={symbol}"
        dir_5m.mkdir(parents=True, exist_ok=True)
        file_5m = dir_5m / "data.parquet"

        time_col = "timestamp" if "timestamp" in df_1m.columns else "date"
        df_5m = (
            df_1m.group_by_dynamic(time_col, every="5m")
            .agg([
                pl.col("open").first(),
                pl.col("high").max(),
                pl.col("low").min(),
                pl.col("close").last(),
                pl.col("volume").sum(),
                pl.lit(symbol).alias("symbol"),
                pl.lit(exchange).alias("exchange")
            ])
            .drop_nulls()
        )
        temp_5m = file_5m.with_suffix(".tmp")
        df_5m.write_parquet(temp_5m, compression="zstd")
        temp_5m.replace(file_5m)

    def flush_all_symbols(self, symbols: List[str], exchange: str = "NSE") -> int:
        """Flushes all symbols in the universe."""
        total_flushed = 0
        for s in symbols:
            try:
                count = self.flush_symbol(exchange, s)
                total_flushed += count
            except Exception as e:
                logger.warning(f"Error flushing candles for {s}: {e}")
        logger.info(f"EOD Flush Complete: {total_flushed} candles written to Silver Parquet.")
        return total_flushed
