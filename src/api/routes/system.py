import os
import sys
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

try:
    import psutil
except ImportError:
    psutil = None

from src.config.settings import settings
from src.api.dependencies import get_services, ServiceContainer

logger = logging.getLogger("SystemRoute")
router = APIRouter(prefix="/api/system", tags=["System & Engine Operations"])

IST = timezone(timedelta(hours=5, minutes=30))


def _get_market_status() -> Dict[str, Any]:
    """Computes current market session state (IST)."""
    now_ist = datetime.now(IST)
    weekday = now_ist.weekday()  # 0=Monday, 4=Friday, 5=Sat, 6=Sun
    time_val = now_ist.time()

    is_weekend = weekday >= 5
    open_time = datetime.strptime("09:15:00", "%H:%M:%S").time()
    close_time = datetime.strptime("15:30:00", "%H:%M:%S").time()

    is_open = (not is_weekend) and (open_time <= time_val <= close_time)
    
    session = "CLOSED"
    if is_weekend:
        session = "WEEKEND_CLOSED"
    elif time_val < open_time:
        session = "PRE_MARKET"
    elif open_time <= time_val <= close_time:
        session = "LIVE_MARKET"
    else:
        session = "POST_MARKET"

    return {
        "is_market_open": is_open,
        "session_state": session,
        "ist_time": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "weekday": now_ist.strftime("%A")
    }


@router.get("/health")
def get_system_health(services: ServiceContainer = Depends(get_services)) -> Dict[str, Any]:
    """
    Returns full telemetry: Redis connectivity, RAM usage, Market status, 
    Lakehouse paths, and active strategy state.
    """
    # 1. Process Memory
    mem_rss_mb = 0.0
    if psutil is not None:
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            mem_rss_mb = round(mem_info.rss / (1024 * 1024), 2)
        except Exception:
            mem_rss_mb = 0.0

    # 2. Redis Connection
    redis_alive = False
    try:
        redis_alive = services.redis_manager.is_alive()
    except Exception:
        redis_alive = False

    # 3. Market Status
    mkt = _get_market_status()

    # 4. Lakehouse Storage Stats
    lakehouse_dir = settings.DATA_DIR / "lakehouse"
    silver_1d = lakehouse_dir / "silver" / "ohlcv_1d"
    silver_1m = lakehouse_dir / "silver" / "ohlcv_1m"
    gold_dir = lakehouse_dir / "gold"

    lakehouse_status = {
        "base_exists": lakehouse_dir.exists(),
        "silver_1d_stocks": len(list(silver_1d.glob("*.parquet"))) if silver_1d.exists() else 0,
        "silver_1m_stocks": len(list(silver_1m.iterdir())) if silver_1m.exists() else 0,
        "gold_features_exists": gold_dir.exists()
    }

    # 5. Portfolio & Engine State
    pm = services.portfolio_manager
    orch = services.gap_orchestrator

    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "memory_rss_mb": mem_rss_mb,
        "market": mkt,
        "redis_connected": redis_alive,
        "lakehouse": lakehouse_status,
        "execution": {
            "mode": settings.EXECUTION_MODE,
            "open_positions": len(pm.positions),
            "circuit_breaker_tripped": pm.circuit_breaker_tripped,
            "orchestrator_running": orch.is_running
        }
    }


@router.post("/sync")
def trigger_system_sync(
    mode: str = "daily",  # 'daily' or 'hybrid' or 'refresh_ranking'
    background_tasks: BackgroundTasks = BackgroundTasks(),
    services: ServiceContainer = Depends(get_services)
):
    """
    Triggers automated Lakehouse synchronization in a background thread.
    - 'daily': Full 2,357-universe 1D sync + Gold feature recalculation
    - 'hybrid': Top 300 Intraday 1M gap resolution
    - 'refresh_ranking': Re-rank Top 300 Turnover Leaders based on 20-day volume
    """
    orch = services.gap_orchestrator

    if orch.is_running:
        return {
            "status": "BUSY",
            "message": "A synchronization job is already running in background."
        }

    def _sync_worker(sync_mode: str):
        try:
            logger.info(f"Starting Background Lakehouse Sync (Mode: {sync_mode})...")
            if sync_mode == "daily":
                orch.sync_1d_universe()
            elif sync_mode == "hybrid":
                orch.sync_hybrid_intraday()
            elif sync_mode == "refresh_ranking":
                orch.refresh_top_universe_ranking()
            else:
                orch.run_full_cycle()
            logger.info(f"Lakehouse Sync ({sync_mode}) completed successfully.")
        except Exception as e:
            logger.error(f"Background Sync failed: {e}", exc_info=True)

    background_tasks.add_task(_sync_worker, mode)

    return {
        "status": "QUEUED",
        "mode": mode,
        "message": f"Sync job '{mode}' initiated in background."
    }


@router.get("/sync/status")
def get_sync_status(services: ServiceContainer = Depends(get_services)):
    """
    Returns current sync execution status.
    """
    orch = services.gap_orchestrator
    return {
        "is_running": orch.is_running,
        "engine": "GapOrchestrator",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
