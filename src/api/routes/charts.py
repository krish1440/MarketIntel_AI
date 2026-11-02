import logging
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends

from src.api.dependencies import ServiceContainer, get_services
from src.api.schemas.charts import ChartResponse, CandleItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/charts", tags=["Charts & Candlesticks"])

@router.get("/{symbol}", response_model=ChartResponse)
def get_chart_candlesticks(
    symbol: str,
    timeframe: str = Query("1m", pattern="^(1m|5m|15m|1h|1d)$", description="Candle timeframe: 1m, 5m, 15m, 1h, 1d"),
    limit: int = Query(500, ge=1, le=2000, description="Max candles to return"),
    lookback_bars: Optional[int] = Query(None, description="Alias for limit"),
    auto_backfill: bool = Query(True, description="When true, automatically backfills missing historical bars on-the-fly"),
    services: ServiceContainer = Depends(get_services)
):
    """
    High-Speed Candlestick Serving API for TradingView Lightweight Charts (<30ms).
    Seamlessly blends historical Parquet data (from DuckDB) with today's live RAM minutes.
    Automatically catches up any missing offline days if auto_backfill is enabled.
    """
    sym = symbol.strip().upper()
    effective_limit = lookback_bars if lookback_bars is not None else limit
    try:
        raw_candles = services.chart_service.get_candlesticks(
            symbol=sym,
            timeframe=timeframe,
            limit=effective_limit,
            exchange="NSE",
            auto_backfill=auto_backfill
        )

        candle_items = []
        for c in raw_candles:
            candle_items.append(CandleItem(
                time=int(c.get("time", 0)),
                open=round(float(c.get("open", 0.0)), 2),
                high=round(float(c.get("high", 0.0)), 2),
                low=round(float(c.get("low", 0.0)), 2),
                close=round(float(c.get("close", 0.0)), 2),
                volume=int(c.get("volume", 0)),
                vwap=round(float(c.get("vwap")), 2) if c.get("vwap") is not None else None
            ))

        return ChartResponse(
            symbol=sym,
            timeframe=timeframe,
            candles_count=len(candle_items),
            candles=candle_items
        )
    except Exception as e:
        logger.error(f"Error serving chart for {sym} ({timeframe}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate chart candles for {sym}: {str(e)}")
