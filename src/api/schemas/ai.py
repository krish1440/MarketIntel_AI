from typing import List, Optional
from pydantic import BaseModel, Field

class CorridorForecast(BaseModel):
    symbol: str
    current_price: float
    p05_floor: float = Field(..., description="10th percentile downside stop floor")
    p25_lower: float = Field(..., description="25th percentile conservative bound")
    p50_median: float = Field(..., description="50th percentile baseline trajectory")
    p75_target1: float = Field(..., description="75th percentile profit target 1")
    q90_runner: float = Field(..., description="90th percentile bullish runner ceiling")
    corridor_width_pct: float
    asymmetry_ratio: float = Field(..., description="Upside potential to downside risk ratio")

class ScreenerCandidateItem(BaseModel):
    rank: int
    symbol: str
    current_price: float
    rank_score: float
    action: str
    confidence_pct: float
    turnover_cr: float

class AISignalResponse(BaseModel):
    symbol: str
    action: str = Field(..., description="STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL")
    confidence_pct: float
    current_price: float
    recommended_entry: float
    dynamic_stop_loss: float
    target_1: float
    target_2: float
    risk_reward_ratio: float
    generated_at: str
