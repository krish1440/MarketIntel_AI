import time
import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from src.config.settings import settings
from src.broker.angel_client import AngelClient
from src.master.security_master import SecurityMaster
from src.serving.streaming_aggregator import StreamingAggregator

logger = logging.getLogger("AngelWebSocket")

class AngelLiveWebSocket:
    """
    Institutional Real-Time Tick Streamer for Angel One SmartAPI (SmartWebSocketV2).
    
    Responsibilities:
      - Authenticates via TOTP session management.
      - Resolves NSE symbols to numeric Angel tokens via SecurityMaster.
      - Streams real-time tick-by-tick prices in background daemon thread.
      - Decodes binary ticks and feeds StreamingAggregator to build 1-min & 5-min candles in RAM.
      - Auto-reconnects with exponential backoff on network disconnections.
    """

    def __init__(
        self,
        angel_client: Optional[AngelClient] = None,
        streaming_aggregator: Optional[StreamingAggregator] = None
    ):
        self.angel = angel_client or AngelClient()
        self.aggregator = streaming_aggregator or StreamingAggregator()
        self.security_master = SecurityMaster()
        
        # Token mapping: symbol -> token, token -> symbol
        self.symbol_to_token: Dict[str, str] = {}
        self.token_to_symbol: Dict[str, str] = {}
        self._load_token_mappings()

        self.sws: Optional[SmartWebSocketV2] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.subscribed_tokens: List[str] = []
        
        # Callbacks
        self.on_tick: Optional[Callable[[str, float, int, int], None]] = None

    def _load_token_mappings(self):
        """Loads official symbol-to-token mappings from SecurityMaster."""
        if self.security_master.df is not None:
            for row in self.security_master.df.select(["nse_symbol", "nse_token"]).iter_rows(named=True):
                sym = row.get("nse_symbol")
                tok = row.get("nse_token")
                if sym and tok:
                    s_str = str(sym).strip()
                    t_str = str(tok).strip()
                    self.symbol_to_token[s_str] = t_str
                    self.token_to_symbol[t_str] = s_str
            logger.info(f"Loaded {len(self.symbol_to_token)} token mappings into memory.")

    def get_token(self, symbol: str) -> Optional[str]:
        return self.symbol_to_token.get(symbol.upper())

    def get_symbol(self, token: str) -> Optional[str]:
        return self.token_to_symbol.get(str(token))

    def connect(self) -> bool:
        """Establishes authenticated live SmartWebSocketV2 connection."""
        if not self.angel.session_data:
            if not self.angel.login():
                logger.error("Failed to authenticate Angel One session for WebSocket.")
                return False

        jwt_token = self.angel.session_data.get("jwtToken")
        feed_token = self.angel.feed_token
        api_key = self.angel.api_key
        client_code = self.angel.client_code

        logger.info(f"Connecting to Angel One SmartWebSocketV2 (Client: {client_code})...")

        try:
            self.sws = SmartWebSocketV2(
                auth_token=jwt_token,
                api_key=api_key,
                client_code=client_code,
                feed_token=feed_token,
                max_retry_attempt=5,
                retry_strategy=1,
                retry_delay=5
            )

            # Assign Callbacks
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close
            self.sws._on_close = lambda wsapp, *args, **kwargs: self._on_close(wsapp, *args, **kwargs)

            # Run in background daemon thread so application remains non-blocking
            self.ws_thread = threading.Thread(target=self.sws.connect, daemon=True, name="AngelWebSocketThread")
            self.ws_thread.start()

            # Wait up to 5 seconds for connection handshake
            for _ in range(10):
                time.sleep(0.5)
                if self.is_connected:
                    logger.info("Angel Live WebSocket handshake confirmed!")
                    return True

            logger.info("WebSocket connection thread started (handshake pending)...")
            return True
        except Exception as e:
            logger.error(f"Failed to start SmartWebSocketV2: {e}")
            return False

    def _on_open(self, wsapp):
        logger.info("Angel One SmartWebSocketV2 connection OPENED successfully.")
        self.is_connected = True
        # Re-subscribe tokens if any were registered
        if self.subscribed_tokens:
            self._do_subscribe(self.subscribed_tokens)

    def _on_data(self, wsapp, message: Dict[str, Any]):
        """Processes incoming real-time market tick."""
        try:
            tok = str(message.get("token", ""))
            symbol = self.get_symbol(tok)
            if not symbol:
                return

            # Price in SmartWebSocketV2 is in paise (divide by 100 for Rupees)
            raw_ltp = message.get("last_traded_price", 0.0)
            ltp = float(raw_ltp) / 100.0 if raw_ltp > 10000 else float(raw_ltp)
            
            raw_qty = message.get("last_traded_quantity", 1)
            qty = int(raw_qty) if raw_qty else 1
            
            ts = message.get("exchange_timestamp", int(time.time()))
            if ts and ts > 1e12:  # Milliseconds to seconds
                ts = int(ts / 1000)

            # 1. Feed into In-Memory Streaming Aggregator to build 1m and 5m bars in RAM
            self.aggregator.process_tick(
                exchange="NSE",
                symbol=symbol,
                price=ltp,
                qty=qty,
                timestamp=ts
            )

            # 2. Invoke optional tick listener
            if self.on_tick:
                self.on_tick(symbol, ltp, qty, ts)

        except Exception as e:
            logger.debug(f"Error parsing WebSocket tick: {e}")

    def _on_error(self, wsapp, error):
        logger.error(f"Angel WebSocket Error: {error}")

    def _on_close(self, wsapp, *args):
        logger.warning("Angel WebSocket connection CLOSED.")
        self.is_connected = False

    def subscribe_symbols(self, symbols: List[str], mode: int = 2):
        """
        Subscribes to live ticks for given NSE symbols.
        Mode: 1=LTP, 2=Quote (LTP, Vol, OHLC), 3=SnapQuote
        """
        tokens = []
        for s in symbols:
            tok = self.get_token(s)
            if tok:
                tokens.append(tok)
            else:
                logger.warning(f"Symbol {s} has no token mapping in SecurityMaster.")

        if not tokens:
            logger.warning("No valid tokens found to subscribe.")
            return

        self.subscribed_tokens = list(set(self.subscribed_tokens + tokens))
        if self.is_connected and self.sws:
            self._do_subscribe(tokens, mode=mode)
        else:
            logger.info(f"Queued {len(tokens)} tokens for subscription once connected.")

    def _do_subscribe(self, tokens: List[str], mode: int = 2):
        """Executes subscription payload on active connection."""
        correlation_id = f"MKT_{int(time.time())}"[-10:]
        token_payload = [
            {
                "exchangeType": 1,  # 1 = NSE_CM
                "tokens": tokens
            }
        ]
        try:
            self.sws.subscribe(correlation_id=correlation_id, mode=mode, token_list=token_payload)
            logger.info(f"Subscribed to {len(tokens)} symbols on live feed (Mode: {mode}).")
        except Exception as e:
            logger.error(f"Failed to subscribe tokens: {e}")

    def close(self):
        """Gracefully disconnects WebSocket."""
        logger.info("Closing Angel Live WebSocket...")
        self.is_connected = False
        if self.sws:
            try:
                self.sws.close_connection()
            except Exception:
                pass
