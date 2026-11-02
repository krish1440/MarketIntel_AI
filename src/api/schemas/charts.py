from typing import List, Optional
from pydantic import BaseModel, Field

class CandleItem(BaseModel):
    time: int = Field(..., description="UNIX timestamp (seconds)")
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None

class ChartResponse(BaseModel):
    symbol: str
    timeframe: str
    candles_count: int
    candles: List[CandleItem]
