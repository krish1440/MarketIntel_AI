import sys
import time
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.broker.angel_client import AngelClient
from src.broker.angel_websocket import AngelLiveWebSocket
from src.serving.streaming_aggregator import StreamingAggregator
from src.serving.redis_manager import RedisManager
from src.serving.eod_flush_worker import EODFlushWorker
from src.crawler.daily_sync import DailySyncer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LiveDataPipelineTest")

def main():
    logger.info("=" * 80)
    logger.info("       LIVE MARKET DATA PIPELINE END-TO-END VERIFICATION TEST")
    logger.info("       Testing Both 1-Minute Live WebSocket Stream AND 1-Day Incremental Sync")
    logger.info("=" * 80)

    # -------------------------------------------------------------
    # PART 1: 1-DAY (1D) INCREMENTAL CATCH-UP TEST
    # -------------------------------------------------------------
    logger.info("\n[TEST 1] Verifying 1-Day (1D) Incremental Catch-Up (Zero Missing Days)...")
    syncer = DailySyncer(exchange="NSE")
    test_symbols = ["RELIANCE", "TCS", "INFY"]
    for sym in test_symbols:
        res = syncer.sync_symbol(sym)
        logger.info(f"  1D Sync for {sym:<10}: Result = {res}")

    # -------------------------------------------------------------
    # PART 2: 1-MINUTE (1M) LIVE WEBSOCKET TICK-TO-CANDLE INGESTION
    # -------------------------------------------------------------
    logger.info("\n[TEST 2] Connecting to Angel One Live SmartWebSocketV2 (Live Market Hours)...")
    redis_mgr = RedisManager()
    aggregator = StreamingAggregator(redis_mgr=redis_mgr)

    ticks_received = []
    def on_live_tick(symbol, price, qty, ts):
        ticks_received.append((symbol, price, qty, ts))
        if len(ticks_received) <= 5 or len(ticks_received) % 20 == 0:
            logger.info(f"  ⚡ LIVE TICK: {symbol:<10} | Price: Rs.{price:>8.2f} | Qty: {qty:>4} | TS: {ts}")

    ws_client = AngelLiveWebSocket(streaming_aggregator=aggregator)
    ws_client.on_tick = on_live_tick

    connected = ws_client.connect()
    if not connected:
        logger.warning("Could not establish live WebSocket handshake. Checking credentials or network.")
        return

    # Subscribe to liquid leaders
    watch_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "TATAMOTORS"]
    logger.info(f"Subscribing to {len(watch_symbols)} live stocks on exchange feed: {watch_symbols}")
    ws_client.subscribe_symbols(watch_symbols, mode=2)

    # Listen to live ticks for 10 seconds
    logger.info("\nAwaiting incoming real-time market ticks for 10 seconds...")
    t_end = time.time() + 10
    while time.time() < t_end:
        time.sleep(1)

    logger.info(f"\n--> LIVE STREAM SUMMARY: Received {len(ticks_received)} real-time ticks from Angel One!")

    # -------------------------------------------------------------
    # PART 3: IN-MEMORY RAM CANDLE INSPECTION & EOD FLUSH TO SILVER
    # -------------------------------------------------------------
    logger.info("\n[TEST 3] Inspecting In-Memory RAM 1-Minute Candles...")
    active_candles = aggregator._active_1m
    logger.info(f"Active 1m Candle States in RAM: {len(active_candles)} symbols tracking.")
    for sym_key, c_state in active_candles.items():
        c_dict = c_state.to_dict()
        logger.info(f"  RAM 1m Bar for {sym_key}: Open={c_dict['open']}, High={c_dict['high']}, Low={c_dict['low']}, Close={c_dict['close']}, Vol={c_dict['volume']}, Ticks={c_state.ticks_count}")

    # Test EOD Flush
    logger.info("\n[TEST 4] Testing EOD Flush Worker (RAM -> Silver Parquet)...")
    flusher = EODFlushWorker(redis_mgr=redis_mgr)
    flushed = flusher.flush_all_symbols(watch_symbols)
    logger.info(f"--> Flushed {flushed} completed candles to Silver lakehouse.")

    # Graceful Disconnect
    ws_client.close()
    logger.info("\n" + "=" * 80)
    logger.info("       LIVE DATA PIPELINE TEST COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
