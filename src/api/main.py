import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from datetime import datetime, timezone, timedelta
from src.config.settings import settings
from src.api.dependencies import ServiceContainer
from src.api.ws.connection_manager import ws_manager
from src.serving.focus_universe_service import FocusUniverseService
from src.api.routes.stocks import router as stocks_router
from src.api.routes.charts import router as charts_router
from src.api.routes.ai import router as ai_router
from src.api.routes.trading import router as trading_router
from src.api.routes.system import router as system_router
from src.api.ws.endpoint import router as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MarketIntelAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan:
    Initializes high-speed DuckDB connections, Security Master catalog,
    Redis/InMemory cache, and AI Paper Trading engine on startup.
    Also starts live Angel One SmartAPI tick streamer during market hours.
    """
    logger.info("Initializing MarketIntel Institutional Platform Services...")
    services = ServiceContainer.get_instance()
    services.main_loop = asyncio.get_running_loop()

    # Initialize live broker market data feeder
    try:
        from src.broker.angel_websocket import AngelLiveWebSocket
        live_ws = AngelLiveWebSocket(streaming_aggregator=services.streaming_aggregator)
        services.live_ws = live_ws

        def on_tick_callback(symbol: str, price: float, qty: int, ts: int):
            tick_msg = {
                "type": "TICK",
                "data": {
                    "symbol": symbol,
                    "ltp": price,
                    "close": price,
                    "volume": qty,
                    "timestamp": ts
                }
            }
            if services.main_loop and services.main_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast("live", tick_msg),
                    services.main_loop
                )

        live_ws.on_tick = on_tick_callback
        connected = live_ws.connect()
        if connected:
            # Dynamically resolve today's AI focus watchlist + active positions
            focus_service = FocusUniverseService(services)
            focus_symbols = focus_service.get_today_focus_symbols(watchlist_size=40)
            live_ws.subscribe_symbols(focus_symbols)
            logger.info(f"Angel One live tick feeder active for {len(focus_symbols)} dynamic focus equities.")
        else:
            logger.warning("Could not establish Angel One live websocket; falling back to simulation if needed.")
    except Exception as e:
        logger.error(f"Error initializing live market feeder: {e}", exc_info=True)

    # Automated 09:15 AM Market-Open Focus Watchlist Refresher
    async def market_open_focus_refresher():
        """Periodic background worker checking for market open (09:15:30 IST) to refresh AI focus candidates."""
        while True:
            try:
                await asyncio.sleep(60)
                now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
                # Check if weekday (Monday-Friday) and within the 09:15-09:17 AM market open window
                if now_ist.weekday() < 5 and now_ist.hour == 9 and now_ist.minute in [15, 16]:
                    if services.live_ws:
                        f_srv = FocusUniverseService(services)
                        fresh_syms = f_srv.get_today_focus_symbols(watchlist_size=40)
                        services.live_ws.subscribe_symbols(fresh_syms)
                        logger.info(f"Market-open focus watchlist refreshed: {len(fresh_syms)} equities actively streaming.")
                        await asyncio.sleep(120)  # Sleep past market-open window
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.debug(f"Error in market_open_focus_refresher: {ex}")

    refresher_task = asyncio.create_task(market_open_focus_refresher())

    logger.info(
        f"Platform ready. Master Equities: {len(services.security_master.df) if services.security_master.df is not None else 0} | "
        f"Execution Mode: {settings.EXECUTION_MODE}"
    )
    yield
    logger.info("Shutting down MarketIntel API server cleanly.")
    refresher_task.cancel()
    if services.live_ws:
        try:
            services.live_ws.close()
        except Exception:
            pass


app = FastAPI(
    title="MarketIntel Institutional Analytics & AI Paper Trading API",
    version="2.0.0",
    description="High-throughput institutional market intelligence, multi-timeframe OHLCV charts, AI signals, and risk-governed simulated execution for Indian Equities (NSE/BSE).",
    lifespan=lifespan
)

# CORS Middleware for modern React / Next.js / Vite frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(stocks_router)
app.include_router(charts_router)
app.include_router(ai_router)
app.include_router(trading_router)
app.include_router(system_router)
app.include_router(ws_router)


@app.get("/", tags=["Root"])
def root_status():
    """Root healthcheck and platform overview."""
    return {
        "platform": "MarketIntel Institutional Engine",
        "version": "2.0.0",
        "status": "ONLINE",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "supported_timeframes": ["1m", "5m", "15m", "1h", "1d"],
        "modules": {
            "stocks": "/api/stocks",
            "charts": "/api/charts",
            "ai": "/api/ai",
            "trading": "/api/trading",
            "system": "/api/system",
            "websockets": "/ws"
        }
    }

