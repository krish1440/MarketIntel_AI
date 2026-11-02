from typing import List, Optional
from pydantic import BaseModel, Field

class PortfolioSummaryResponse(BaseModel):
    initial_capital: float
    current_cash: float
    total_portfolio_value: float
    total_invested: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_return_pct: float
    open_positions_count: int
    max_drawdown_pct: float
    daily_pnl_pct: float
    circuit_breaker_tripped: bool

class PositionItem(BaseModel):
    symbol: str
    trade_id: str
    entry_time: str
    entry_price: float
    quantity: int
    current_price: float
    allocated_capital: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    ml_stop_price: float
    ml_target_1: float
    ml_target_2: float
    partial_exit_done: bool
    highest_price_seen: float

class TradeItem(BaseModel):
    trade_id: str
    symbol: str
    entry_time: str
    exit_time: str
    holding_days: int
    quantity: int
    entry_price: float
    exit_price: float
    gross_pnl: float
    gross_pnl_pct: float
    total_transaction_frictions: float
    capital_gains_tax: float
    tax_type: str
    net_pnl: float
    net_pnl_pct: float
    exit_trigger: str

class ManualOrderRequest(BaseModel):
    symbol: str
    direction: str = Field(default="BUY", description="BUY or SELL")
    quantity: Optional[int] = Field(None, description="Shares quantity, or auto-sized if None")
    price: Optional[float] = Field(None, description="Limit price or Market price if None")

