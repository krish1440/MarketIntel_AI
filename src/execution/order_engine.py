import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Tuple

logger = logging.getLogger("OrderEngine")

class OrderDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class TransactionFrictions:
    """Detailed statutory transaction breakdown for Indian Equities."""
    stt: float                     # Securities Transaction Tax
    exchange_charges: float        # NSE/BSE turnover charges
    sebi_fees: float               # SEBI turnover fees
    stamp_duty: float              # State stamp duty
    brokerage: float               # Brokerage charges
    gst: float                     # 18% GST on (Brokerage + Exchange)
    total_statutory_charges: float # Sum of all friction costs

@dataclass
class OrderRequest:
    symbol: str
    direction: OrderDirection
    quantity: int
    requested_price: float
    order_type: OrderType = OrderType.MARKET
    trigger_reason: str = "MANUAL"
    is_delivery: bool = True
    order_time: Optional[datetime] = None

@dataclass
class OrderExecution:
    order_id: str
    symbol: str
    direction: OrderDirection
    order_type: OrderType
    trigger_reason: str
    quantity: int
    requested_price: float
    filled_price: float
    slippage_cost: float
    statutory_charges: TransactionFrictions
    total_cash_impact: float       # Total cash debited (buy) or credited (sell)
    fill_time: datetime
    status: OrderStatus

@dataclass
class TradeExitResult:
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    holding_days: int
    quantity: int
    entry_price: float
    exit_price: float
    gross_pnl: float
    gross_pnl_pct: float
    total_transaction_frictions: float
    pre_tax_pnl: float
    capital_gains_tax: float
    tax_type: str                  # "STCG_20%" or "LTCG_12.5%" or "NONE (LOSS)"
    net_pnl: float
    net_pnl_pct: float
    exit_trigger: str

class IndianTaxEngine:
    """
    Institutional Statutory Indian Tax & Friction Calculator.
    
    1. Transaction Costs (Turnover-based):
       - STT: 0.1% on delivery (both Buy & Sell) / 0.025% on intraday Sell.
       - Exchange Turnover: 0.00345% of total turnover.
       - SEBI Fees: ₹10 per crore (0.0001%).
       - Stamp Duty: 0.015% on delivery Buy / 0.003% on intraday Buy.
       - Brokerage: ₹20 flat per executed order.
       - GST: 18% on (Brokerage + Exchange Charges).
       
    2. Capital Gains Tax (Holding Period-based):
       - STCG (< 365 Days): 20.0% on realized net gain (Finance Act 2024+).
       - LTCG (>= 365 Days): 12.5% on realized net gain exceeding ₹1.25L exemption threshold.
    """

    STT_DELIVERY_RATE = 0.001          # 0.1% Buy & Sell
    STT_INTRADAY_SELL_RATE = 0.00025   # 0.025% Sell only
    EXCHANGE_TURNOVER_RATE = 0.0000345 # 0.00345%
    SEBI_TURNOVER_RATE = 0.000001      # ₹10 per Crore (0.0001%)
    STAMP_DUTY_DELIVERY = 0.00015      # 0.015% Buy only
    STAMP_DUTY_INTRADAY = 0.00003      # 0.003% Buy only
    BROKERAGE_PER_ORDER = 20.0         # ₹20 flat
    GST_RATE = 0.18                    # 18% GST

    STCG_RATE = 0.20                   # 20% Short-Term (< 1 Year)
    LTCG_RATE = 0.125                  # 12.5% Long-Term (>= 1 Year)
    LTCG_EXEMPTION_THRESHOLD = 125000  # ₹1.25 Lakh cumulative annual exemption

    def __init__(self, ltcg_exemption_utilized: float = 0.0):
        self.ltcg_exemption_utilized = ltcg_exemption_utilized

    def calculate_frictions(
        self, 
        price: float, 
        quantity: int, 
        direction: OrderDirection, 
        is_delivery: bool = True
    ) -> TransactionFrictions:
        """Calculates exact statutory deductions for a single order fill."""
        turnover = price * quantity

        # STT
        if is_delivery:
            stt = turnover * self.STT_DELIVERY_RATE
        else:
            stt = turnover * self.STT_INTRADAY_SELL_RATE if direction == OrderDirection.SELL else 0.0

        # Exchange & SEBI
        exchange = turnover * self.EXCHANGE_TURNOVER_RATE
        sebi = turnover * self.SEBI_TURNOVER_RATE

        # Stamp Duty (Buy side only)
        if direction == OrderDirection.BUY:
            stamp = turnover * (self.STAMP_DUTY_DELIVERY if is_delivery else self.STAMP_DUTY_INTRADAY)
        else:
            stamp = 0.0

        brokerage = self.BROKERAGE_PER_ORDER
        gst = (brokerage + exchange) * self.GST_RATE

        total = stt + exchange + sebi + stamp + brokerage + gst

        return TransactionFrictions(
            stt=round(stt, 2),
            exchange_charges=round(exchange, 2),
            sebi_fees=round(sebi, 2),
            stamp_duty=round(stamp, 2),
            brokerage=round(brokerage, 2),
            gst=round(gst, 2),
            total_statutory_charges=round(total, 2)
        )

    def calculate_capital_gains(self, pre_tax_profit: float, holding_days: int) -> Tuple[float, str]:
        """Calculates holding-period dependent Capital Gains Tax (STCG vs LTCG)."""
        if pre_tax_profit <= 0:
            return 0.0, "NONE (LOSS)"

        if holding_days < 365:
            # Short-Term Capital Gains (20.0%)
            tax = pre_tax_profit * self.STCG_RATE
            return round(tax, 2), "STCG_20%"
        else:
            # Long-Term Capital Gains (12.5% on amount exceeding ₹1.25L exemption)
            remaining_exemption = max(0.0, self.LTCG_EXEMPTION_THRESHOLD - self.ltcg_exemption_utilized)
            taxable_gain = max(0.0, pre_tax_profit - remaining_exemption)
            self.ltcg_exemption_utilized += min(pre_tax_profit, remaining_exemption)
            tax = taxable_gain * self.LTCG_RATE
            return round(tax, 2), "LTCG_12.5%"

class SimulatedOrderEngine:
    """
    Institutional Virtual Order Matching Engine.
    Simulates real-world execution with bid-ask slippage and Indian statutory tax deductions.
    """

    DEFAULT_SLIPPAGE_PCT = 0.0005  # 0.05% slippage on market orders

    def __init__(self, slippage_pct: float = DEFAULT_SLIPPAGE_PCT):
        self.slippage_pct = slippage_pct
        self.tax_engine = IndianTaxEngine()

    def execute_order(self, request: OrderRequest, current_tick_price: float) -> OrderExecution:
        """
        Executes a paper order against current market price applying realistic slippage.
        """
        order_time = request.order_time or datetime.now(timezone.utc)
        order_id = str(uuid.uuid4())

        # Slippage simulation: Buy orders pay slightly more; Sell orders receive slightly less
        if request.order_type == OrderType.MARKET:
            if request.direction == OrderDirection.BUY:
                filled_price = current_tick_price * (1.0 + self.slippage_pct)
            else:
                filled_price = current_tick_price * (1.0 - self.slippage_pct)
            slippage_cost = abs(filled_price - current_tick_price) * request.quantity
        else:
            # Limit or stop fill at exact requested price
            filled_price = request.requested_price
            slippage_cost = 0.0

        # Calculate statutory frictions
        frictions = self.tax_engine.calculate_frictions(
            price=filled_price,
            quantity=request.quantity,
            direction=request.direction,
            is_delivery=request.is_delivery
        )

        turnover = filled_price * request.quantity

        if request.direction == OrderDirection.BUY:
            total_cash_impact = -(turnover + frictions.total_statutory_charges)
        else:
            total_cash_impact = +(turnover - frictions.total_statutory_charges)

        return OrderExecution(
            order_id=order_id,
            symbol=request.symbol,
            direction=request.direction,
            order_type=request.order_type,
            trigger_reason=request.trigger_reason,
            quantity=request.quantity,
            requested_price=round(request.requested_price, 2),
            filled_price=round(filled_price, 2),
            slippage_cost=round(slippage_cost, 2),
            statutory_charges=frictions,
            total_cash_impact=round(total_cash_impact, 2),
            fill_time=order_time,
            status=OrderStatus.FILLED
        )

    def calculate_trade_close(
        self,
        trade_id: str,
        symbol: str,
        entry_time: datetime,
        exit_time: datetime,
        entry_price: float,
        exit_price: float,
        quantity: int,
        entry_frictions: float,
        exit_frictions: float,
        exit_trigger: str
    ) -> TradeExitResult:
        """Calculates final trade settlement including gross PnL, frictions, and STCG/LTCG taxes."""
        gross_pnl = (exit_price - entry_price) * quantity
        gross_pnl_pct = ((exit_price / entry_price) - 1.0) * 100.0
        total_frictions = entry_frictions + exit_frictions
        pre_tax_pnl = gross_pnl - total_frictions

        holding_days = max(1, (exit_time - entry_time).days)
        capital_gains_tax, tax_type = self.tax_engine.calculate_capital_gains(pre_tax_pnl, holding_days)

        net_pnl = pre_tax_pnl - capital_gains_tax
        invested_capital = entry_price * quantity
        net_pnl_pct = (net_pnl / invested_capital) * 100.0

        return TradeExitResult(
            trade_id=trade_id,
            symbol=symbol,
            entry_time=entry_time,
            exit_time=exit_time,
            holding_days=holding_days,
            quantity=quantity,
            entry_price=round(entry_price, 2),
            exit_price=round(exit_price, 2),
            gross_pnl=round(gross_pnl, 2),
            gross_pnl_pct=round(gross_pnl_pct, 2),
            total_transaction_frictions=round(total_frictions, 2),
            pre_tax_pnl=round(pre_tax_pnl, 2),
            capital_gains_tax=round(capital_gains_tax, 2),
            tax_type=tax_type,
            net_pnl=round(net_pnl, 2),
            net_pnl_pct=round(net_pnl_pct, 2),
            exit_trigger=exit_trigger
        )
