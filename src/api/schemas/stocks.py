from typing import List, Optional
from pydantic import BaseModel, Field

class StockSearchResult(BaseModel):
    symbol: str = Field(..., description="NSE Trading Symbol")
    company_name: str = Field(..., description="Full Company Name")
    exchange: str = Field(default="NSE", description="Primary Exchange")
    token: Optional[str] = Field(None, description="Angel Instrument Token")
    isin: Optional[str] = Field(None, description="ISIN Code")
    is_top_300: bool = Field(default=False, description="Whether stock is in Top 300 turnover universe")

class StockQuote(BaseModel):
    symbol: str
    exchange: str = "NSE"
    ltp: float
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: int
    pct_change: float
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    updated_at: str

class TopUniverseItem(BaseModel):
    symbol: str
    price: float
    turnover_20d_cr: float
    rank: int

class MarketBreadth(BaseModel):
    advances: int
    declines: int
    unchanged: int
    adv_dec_ratio: float
    timestamp: str
