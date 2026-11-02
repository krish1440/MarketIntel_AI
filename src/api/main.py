import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import settings
from src.api.dependencies import ServiceContainer
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
    """
    logger.info("Initializing MarketIntel Institutional Platform Services...")
    services = ServiceContainer.get_instance()
    logger.info(
        f"Platform ready. Master Equities: {len(services.security_master.df) if services.security_master.df is not None else 0} | "
        f"Execution Mode: {settings.EXECUTION_MODE}"
    )
    yield
    logger.info("Shutting down MarketIntel API server cleanly.")


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
