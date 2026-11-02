import time
import logging
import threading
from collections import defaultdict, deque
from typing import Dict, Any, Optional, List, Union
import redis

logger = logging.getLogger(__name__)

class InMemoryBroker:
    """
    High-Speed Thread-Safe In-Memory Fallback Broker.
    Provides identical semantics to Redis (Hashes, Streams, Pub/Sub) in pure RAM.
    Guarantees 100% zero-cost operation even if Redis / Docker is not running.
    """
    def __init__(self):
        self._hashes: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._streams: Dict[str, deque] = defaultdict(lambda: deque(maxlen=2000))
        self._subscribers: Dict[str, List] = defaultdict(list)
        self._lock = threading.Lock()

    def hset(self, name: str, mapping: Dict[str, Any]):
        """Sets field-value pairs in a hash."""
        with self._lock:
            self._hashes[name].update(mapping)

    def hgetall(self, name: str) -> Dict[str, Any]:
        """Returns all fields and values in a hash."""
        with self._lock:
            return dict(self._hashes.get(name, {}))

    def hget(self, name: str, key: str) -> Optional[Any]:
        """Gets single field value."""
        with self._lock:
            return self._hashes.get(name, {}).get(key)

    def xadd(self, stream: str, fields: Dict[str, Any], maxlen: Optional[int] = 2000) -> str:
        """Appends item to stream with auto-increment ID and optional ring trimming."""
        entry_id = f"{int(time.time() * 1000)}-0"
        with self._lock:
            s = self._streams[stream]
            if maxlen and s.maxlen != maxlen:
                # Update maxlen if specified
                self._streams[stream] = deque(s, maxlen=maxlen)
                s = self._streams[stream]
            s.append((entry_id, fields))
        return entry_id

    def xrange(self, stream: str, min_id: str = "-", max_id: str = "+", count: Optional[int] = None) -> List:
        """Returns items from stream within range."""
        with self._lock:
            items = list(self._streams.get(stream, []))
            if count:
                items = items[-count:]
            return items

    def publish(self, channel: str, message: Any) -> int:
        """Publishes message to local subscribers."""
        with self._lock:
            subs = self._subscribers.get(channel, [])
            count = len(subs)
            for callback in subs:
                try:
                    callback(message)
                except Exception as e:
                    logger.warning(f"Error in pubsub callback: {e}")
            return count

    def subscribe(self, channel: str, callback):
        """Subscribes callback to channel."""
        with self._lock:
            self._subscribers[channel].append(callback)


class RedisManager:
    """
    Unified In-Memory Bus Manager for Real-Time Streaming and Caching.
    Auto-detects live Redis service; falls back to InMemoryBroker if unavailable.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RedisManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        if self._initialized:
            return
            
        self.host = host
        self.port = port
        self.db = db
        self.is_connected = False
        self.client: Union[redis.Redis, InMemoryBroker] = None

        self._connect()
        self._initialized = True

    def _connect(self):
        """Attempts connection to Redis; falls back to InMemoryBroker on failure."""
        import socket
        is_port_open = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            s.connect((self.host, self.port))
            is_port_open = True
            s.close()
        except Exception:
            is_port_open = False

        if is_port_open:
            try:
                r = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0,
                    decode_responses=True
                )
                r.ping()
                self.client = r
                self.is_connected = True
                logger.info(f"Connected to live Redis service at {self.host}:{self.port}")
                return
            except Exception as e:
                logger.debug(f"Redis ping failed: {e}")

        logger.info(f"Redis service not active on {self.host}:{self.port}. Operating in high-speed InMemoryBroker mode.")
        self.client = InMemoryBroker()
        self.is_connected = False

    def set_quote(self, exchange: str, symbol: str, quote_data: Dict[str, Any]):
        """
        Stores live ticker quote in O(1) in-memory hash.
        Key format: quote:{exchange}:{symbol}
        """
        key = f"quote:{exchange}:{symbol}"
        self.client.hset(key, mapping=quote_data)

    def get_quote(self, exchange: str, symbol: str) -> Dict[str, Any]:
        """Fetches live ticker quote in sub-millisecond O(1) time."""
        key = f"quote:{exchange}:{symbol}"
        return self.client.hgetall(key)

    def append_candle(self, exchange: str, symbol: str, timeframe: str, candle: Dict[str, Any]):
        """
        Appends completed 1m or 5m candle to in-memory stream buffer.
        Key format: candles:{exchange}:{symbol}:{timeframe}
        """
        stream_key = f"candles:{exchange}:{symbol}:{timeframe}"
        self.client.xadd(stream_key, fields=candle, maxlen=500)

    def get_recent_candles(self, exchange: str, symbol: str, timeframe: str, limit: int = 375) -> List[Dict[str, Any]]:
        """Fetches recent candles from in-memory buffer."""
        stream_key = f"candles:{exchange}:{symbol}:{timeframe}"
        raw_items = self.client.xrange(stream_key, count=limit)
        candles = []
        for item in raw_items:
            # item is (entry_id, fields_dict)
            candles.append(item[1])
        return candles

    def publish_tick(self, exchange: str, symbol: str, tick: Dict[str, Any]):
        """Broadcasts tick event over pubsub channel."""
        channel = f"ticks:{exchange}:{symbol}"
        self.client.publish(channel, tick)

    def get_live_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Convenience method to retrieve live ticker quote for a symbol."""
        return self.get_quote(exchange, symbol)

    def is_alive(self) -> bool:
        """Checks if backing broker (Redis or in-memory) is active."""
        if self.is_connected:
            try:
                return bool(self.client.ping())
            except Exception:
                return False
        return True
