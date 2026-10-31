import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from src.serving.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class CandleState:
    """Maintains mutable real-time state for an uncompleted candle bar."""
    def __init__(self, start_timestamp: int):
        self.start_timestamp = start_timestamp
        self.open = 0.0
        self.high = 0.0
        self.low = float('inf')
        self.close = 0.0
        self.volume = 0
        self.vwap_sum_pv = 0.0
        self.vwap_sum_v = 0
        self.ticks_count = 0

    def update(self, price: float, qty: int):
        if self.ticks_count == 0:
            self.open = price
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += qty
        self.vwap_sum_pv += (price * qty)
        self.vwap_sum_v += qty
        self.ticks_count += 1

    def to_dict(self) -> Dict[str, Any]:
        vwap = (self.vwap_sum_pv / self.vwap_sum_v) if self.vwap_sum_v > 0 else self.close
        return {
            "timestamp": self.start_timestamp,
            "open": round(self.open, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "close": round(self.close, 2),
            "volume": self.volume,
            "vwap": round(vwap, 2)
        }


class StreamingAggregator:
    """
    Real-Time Tick-to-Candle Streaming Aggregator.
    Ingests live broker ticks and constructs 1-minute and 5-minute candlestick bars
    purely in RAM with zero disk overhead.
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.redis = redis_mgr or RedisManager()
        # Active 1-minute candle state: key = (exchange, symbol)
        self._active_1m: Dict[str, CandleState] = {}
        # Buffer of completed 1m candles awaiting 5m aggregation
        self._buffer_5m: Dict[str, list] = {}
        # Daily running stats for quote
        self._daily_stats: Dict[str, Dict[str, Any]] = {}
        # Optional callback for sealed candles
        self.on_candle_sealed: Optional[Callable[[str, str, str, Dict[str, Any]], None]] = None

    def process_tick(
        self,
        exchange: str,
        symbol: str,
        price: float,
        qty: int,
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processes a single incoming market tick in sub-microsecond time.
        timestamp: UNIX epoch timestamp in seconds.
        """
        ts = timestamp or int(time.time())
        key = f"{exchange}:{symbol}"
        minute_start = (ts // 60) * 60

        # 1. Update Daily Stats for Instant Ticker Hash
        if key not in self._daily_stats:
            self._daily_stats[key] = {
                "open": price, "high": price, "low": price, "close": price,
                "volume": 0, "prev_close": price
            }
        
        d_stat = self._daily_stats[key]
        d_stat["high"] = max(d_stat["high"], price)
        d_stat["low"] = min(d_stat["low"], price)
        d_stat["close"] = price
        d_stat["volume"] += qty
        change_pct = round(((price - d_stat["prev_close"]) / (d_stat["prev_close"] + 1e-8)) * 100, 2)

        # Update Redis Ticker Hash
        quote_data = {
            "symbol": symbol,
            "exchange": exchange,
            "ltp": str(price),
            "open": str(d_stat["open"]),
            "high": str(d_stat["high"]),
            "low": str(d_stat["low"]),
            "close": str(price),
            "volume": str(d_stat["volume"]),
            "change_pct": str(change_pct),
            "updated_at": str(ts)
        }
        self.redis.set_quote(exchange, symbol, quote_data)

        # 2. Check if Current 1-Minute Candle must be sealed
        current_candle = self._active_1m.get(key)
        if current_candle is not None and current_candle.start_timestamp != minute_start:
            # Seal completed 1m candle
            sealed_1m = current_candle.to_dict()
            self._seal_1m_candle(exchange, symbol, sealed_1m)

            # Start fresh 1m candle for the new minute
            current_candle = CandleState(minute_start)
            self._active_1m[key] = current_candle
        elif current_candle is None:
            current_candle = CandleState(minute_start)
            self._active_1m[key] = current_candle

        # 3. Accumulate tick into active 1-minute candle
        current_candle.update(price, qty)

        return quote_data

    def _seal_1m_candle(self, exchange: str, symbol: str, candle: Dict[str, Any]):
        """Persists completed 1-minute candle to Redis and updates 5m aggregator."""
        key = f"{exchange}:{symbol}"
        
        # 1. Push to Redis 1m stream
        self.redis.append_candle(exchange, symbol, "1m", candle)

        if self.on_candle_sealed:
            self.on_candle_sealed(exchange, symbol, "1m", candle)

        # 2. Accumulate into 5-minute buffer
        if key not in self._buffer_5m:
            self._buffer_5m[key] = []
        
        buf = self._buffer_5m[key]
        buf.append(candle)

        if len(buf) >= 5:
            # Seal 5-minute candle
            c_5m = {
                "timestamp": buf[0]["timestamp"],
                "open": buf[0]["open"],
                "high": max(c["high"] for c in buf),
                "low": min(c["low"] for c in buf),
                "close": buf[-1]["close"],
                "volume": sum(c["volume"] for c in buf),
                "vwap": round(sum(c["vwap"] * c["volume"] for c in buf) / (sum(c["volume"] for c in buf) + 1e-8), 2)
            }
            self.redis.append_candle(exchange, symbol, "5m", c_5m)

            if self.on_candle_sealed:
                self.on_candle_sealed(exchange, symbol, "5m", c_5m)

            # Clear 5m buffer
            self._buffer_5m[key] = []
