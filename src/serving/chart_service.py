import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import polars as pl
from src.config.settings import settings
from src.serving.redis_manager import RedisManager
from src.serving.duckdb_client import DuckDBClient

logger = logging.getLogger(__name__)

class ChartService:
    """
    Sub-30ms Hybrid Candlestick Serving Engine for TradingView & Dashboard.
    Seamlessly merges historical Parquet bars (from Silver Lakehouse via DuckDB)
    with today's live minutes (from In-Memory RAM).
    """

    def __init__(self, duck_client: Optional[DuckDBClient] = None, redis_mgr: Optional[RedisManager] = None):
        self.duck = duck_client or DuckDBClient()
        self.redis = redis_mgr or RedisManager()
        self.silver_ohlcv_1m_base = settings.SILVER_DIR / "ohlcv_1m" / "exchange=NSE"
        self.silver_ohlcv_1d_base = settings.SILVER_DIR / "ohlcv_1d" / "exchange=NSE"
        self._intraday_gap_syncer = None
        self._daily_syncer = None

    def get_candlesticks(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 500,
        exchange: str = "NSE",
        auto_backfill: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieves seamless, unified candlestick history in under 30 milliseconds.
        timeframe: '1m', '5m', '1d'
        auto_backfill: When True (default), lazily checks and fills missing gaps on-the-fly.
        Returns TradingView-compliant list of candle dictionaries:
        [{'time': epoch_sec, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': int}]
        """
        start_time = time.time()
        candles = []

        if timeframe == "1d":
            # 1. Daily Candles: Query Silver Lakehouse 1D via DuckDB
            file_path = str(self.silver_ohlcv_1d_base / f"symbol={symbol}" / "data.parquet").replace("\\", "/")
            
            # Lazy backfill if file missing or requested
            if auto_backfill:
                if self._daily_syncer is None:
                    from src.crawler.daily_sync import DailySyncer
                    self._daily_syncer = DailySyncer(exchange=exchange)
                try:
                    self._daily_syncer.sync_symbol(symbol)
                except Exception as e:
                    logger.debug(f"On-demand 1d check for {symbol}: {e}")

            if Path(file_path).exists():
                try:
                    query = f"""
                        SELECT 
                            epoch(date) AS time,
                            open, high, low, close, volume
                        FROM read_parquet('{file_path}')
                        ORDER BY date DESC
                        LIMIT {limit};
                    """
                    df = self.duck.query_df(query)
                    candles = df.reverse().to_dicts()
                except Exception as e:
                    logger.warning(f"Error querying 1d history for {symbol}: {e}")

            # Append today's live running bar from Redis Ticker Hash if market is open
            quote = self.redis.get_quote(exchange, symbol)
            if quote and "ltp" in quote:
                today_epoch = int((time.time() // 86400) * 86400)
                if not candles or candles[-1]["time"] < today_epoch:
                    candles.append({
                        "time": today_epoch,
                        "open": float(quote.get("open", quote["ltp"])),
                        "high": float(quote.get("high", quote["ltp"])),
                        "low": float(quote.get("low", quote["ltp"])),
                        "close": float(quote["ltp"]),
                        "volume": int(float(quote.get("volume", 0)))
                    })

        elif timeframe in ["1m", "5m"]:
            # 2. Intraday 1m/5m Candles: Query Historical Parquet + Live RAM
            file_path = str(self.silver_ohlcv_1m_base / f"symbol={symbol}" / "data.parquet").replace("\\", "/")

            # Lazy On-Demand Gap Backfill for 1-minute data
            if auto_backfill:
                if self._intraday_gap_syncer is None:
                    from src.crawler.intraday_gap_syncer import IntradayGapSyncer
                    self._intraday_gap_syncer = IntradayGapSyncer(exchange=exchange)
                try:
                    gap = self._intraday_gap_syncer.detect_gap(symbol)
                    if gap:
                        logger.info(f"[LAZY ON-DEMAND 1M] Backfilling gap for {symbol} ({gap[0]} to {gap[1]})...")
                        self._intraday_gap_syncer.sync_symbol(symbol)
                except Exception as e:
                    logger.debug(f"Lazy 1m sync notice for {symbol}: {e}")

            if Path(file_path).exists():
                try:
                    query = f"""
                        SELECT 
                            epoch(timestamp) AS time,
                            open, high, low, close, volume
                        FROM read_parquet('{file_path}')
                        ORDER BY timestamp DESC
                        LIMIT {limit};
                    """
                    df = self.duck.query_df(query)
                    candles = df.reverse().to_dicts()
                except Exception as e:
                    logger.warning(f"Error querying {timeframe} history for {symbol}: {e}")

            # Append today's active in-memory candles from Redis
            live_ram_candles = self.redis.get_recent_candles(exchange, symbol, timeframe, limit=375)
            if live_ram_candles:
                seen_times = {c["time"] for c in candles}
                for rc in live_ram_candles:
                    c_time = int(rc["timestamp"])
                    if c_time not in seen_times:
                        candles.append({
                            "time": c_time,
                            "open": float(rc["open"]),
                            "high": float(rc["high"]),
                            "low": float(rc["low"]),
                            "close": float(rc["close"]),
                            "volume": int(rc["volume"])
                        })
                        seen_times.add(c_time)

        elapsed_ms = (time.time() - start_time) * 1000.0
        logger.debug(f"Served {len(candles)} candles for {symbol} ({timeframe}) in {elapsed_ms:.2f}ms")
        return candles[-limit:]
