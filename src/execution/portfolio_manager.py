import os
import sys
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config.settings import settings
from src.execution.order_engine import (
    SimulatedOrderEngine,
    OrderRequest,
    OrderExecution,
    OrderDirection,
    OrderType,
    TradeExitResult
)

logger = logging.getLogger("PortfolioManager")

@dataclass
class Position:
    trade_id: str
    symbol: str
    entry_time: str
    entry_price: float
    quantity: int
    current_price: float
    ml_stop_price: float
    ml_target_1: float
    ml_target_2: float
    allocated_capital: float
    entry_frictions: float
    highest_price_seen: float
    partial_exit_done: bool = False
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

@dataclass
class PortfolioSummary:
    initial_capital: float
    current_cash: float
    invested_capital: float
    total_portfolio_value: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_return_pct: float
    open_positions_count: int
    max_drawdown_pct: float
    daily_pnl_pct: float
    circuit_breaker_tripped: bool

class VirtualPortfolioManager:
    """
    Institutional Virtual Portfolio & Risk Governance Manager.
    
    Guarantees:
      - ₹10,00,000 Initial Virtual Capital.
      - Dynamic Volatility-Adjusted & Conviction-Weighted Capital Sizing.
      - Maximum 5% Capital per Stock (₹50,000 max position size).
      - Maximum 10 Concurrent Open Positions.
      - Daily Portfolio Loss Circuit Breaker (-3.0% maximum daily drawdown halt).
      - Persistent SQLite Ledger for paper orders, active positions, and closed trades.
    """

    DEFAULT_CAPITAL = 1000000.0        # ₹10,00,000 INR
    MAX_CAPITAL_PER_TRADE_PCT = 0.10   # Up to 10% max allocation per position for high conviction
    MAX_OPEN_POSITIONS = 10            # Max 10 simultaneous positions
    RISK_PER_TRADE_PCT = 0.015         # 1.5% account risk (₹15,000) for balanced growth
    DAILY_CIRCUIT_BREAKER_PCT = -0.03  # -3% daily drawdown halt

    def __init__(
        self, 
        initial_capital: float = DEFAULT_CAPITAL,
        db_path: Optional[Path] = None
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.peak_portfolio_value = initial_capital
        self.day_start_portfolio_value = initial_capital
        self.current_trading_date = date.today()
        self.circuit_breaker_tripped = False

        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.order_engine = SimulatedOrderEngine()

        # Database persistence
        self.db_dir = settings.BASE_DIR / "data" / "paper_trading"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (self.db_dir / "paper_ledger.db")
        self._init_database()
        self._load_state()

    def start_new_trading_session(self, current_date: date):
        """Resets daily circuit breaker and establishes day_start baseline for each market session."""
        self.current_trading_date = current_date
        self.day_start_portfolio_value = self.get_portfolio_value()
        self.circuit_breaker_tripped = False

    def _init_database(self):
        """Initializes SQLite tables for persistent orders, positions, and trade history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_positions (
                    symbol TEXT PRIMARY KEY,
                    trade_id TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    current_price REAL NOT NULL,
                    ml_stop_price REAL NOT NULL,
                    ml_target_1 REAL NOT NULL,
                    ml_target_2 REAL NOT NULL,
                    allocated_capital REAL NOT NULL,
                    entry_frictions REAL NOT NULL,
                    highest_price_seen REAL NOT NULL,
                    partial_exit_done INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    trade_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    holding_days INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    gross_pnl REAL NOT NULL,
                    gross_pnl_pct REAL NOT NULL,
                    total_frictions REAL NOT NULL,
                    capital_gains_tax REAL NOT NULL,
                    tax_type TEXT NOT NULL,
                    net_pnl REAL NOT NULL,
                    net_pnl_pct REAL NOT NULL,
                    exit_trigger TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    requested_price REAL NOT NULL,
                    filled_price REAL NOT NULL,
                    slippage REAL NOT NULL,
                    statutory_charges REAL NOT NULL,
                    total_cash_impact REAL NOT NULL,
                    trigger_reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def _load_state(self):
        """Restores portfolio balance and active positions from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM portfolio_state")
            state = dict(cursor.fetchall())
            if "cash" in state:
                self.cash = float(state["cash"])
                self.peak_portfolio_value = float(state.get("peak_portfolio_value", self.cash))
                self.day_start_portfolio_value = float(state.get("day_start_value", self.cash))

            cursor.execute("SELECT * FROM active_positions")
            for row in cursor.fetchall():
                pos = Position(
                    symbol=row[0],
                    trade_id=row[1],
                    entry_time=row[2],
                    entry_price=row[3],
                    quantity=row[4],
                    current_price=row[5],
                    ml_stop_price=row[6],
                    ml_target_1=row[7],
                    ml_target_2=row[8],
                    allocated_capital=row[9],
                    entry_frictions=row[10],
                    highest_price_seen=row[11],
                    partial_exit_done=bool(row[12])
                )
                self.positions[pos.symbol] = pos

    def _persist_state(self):
        """Saves current cash and active positions to SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO portfolio_state VALUES ('cash', ?)", (str(self.cash),))
            cursor.execute("INSERT OR REPLACE INTO portfolio_state VALUES ('peak_portfolio_value', ?)", (str(self.peak_portfolio_value),))
            cursor.execute("INSERT OR REPLACE INTO portfolio_state VALUES ('day_start_value', ?)", (str(self.day_start_portfolio_value),))
            
            cursor.execute("DELETE FROM active_positions")
            for pos in self.positions.values():
                cursor.execute("""
                    INSERT INTO active_positions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pos.symbol, pos.trade_id, pos.entry_time, pos.entry_price, pos.quantity,
                    pos.current_price, pos.ml_stop_price, pos.ml_target_1, pos.ml_target_2,
                    pos.allocated_capital, pos.entry_frictions, pos.highest_price_seen,
                    int(pos.partial_exit_done)
                ))
            conn.commit()

    def _record_order(self, exec_res):
        """Records an order fill into SQLite orders table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exec_res.order_id, exec_res.symbol, exec_res.direction.value,
                    exec_res.quantity, exec_res.requested_price, exec_res.filled_price,
                    exec_res.slippage_cost, exec_res.statutory_charges.total_statutory_charges,
                    exec_res.total_cash_impact, exec_res.trigger_reason,
                    exec_res.fill_time.isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to record order {exec_res.order_id}: {e}")

    def _record_trade_settlement(self, settlement: TradeExitResult):
        """Records completed trade exit and taxes into trade_history SQLite table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO trade_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    settlement.trade_id, settlement.symbol, settlement.entry_time.isoformat(),
                    settlement.exit_time.isoformat(), settlement.holding_days, settlement.quantity,
                    settlement.entry_price, settlement.exit_price, settlement.gross_pnl,
                    settlement.gross_pnl_pct, settlement.total_transaction_frictions,
                    settlement.capital_gains_tax, settlement.tax_type, settlement.net_pnl,
                    settlement.net_pnl_pct, settlement.exit_trigger
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to record settlement for {settlement.symbol}: {e}")

    def calculate_position_size(
        self,
        symbol: str,
        current_price: float,
        ml_stop_price: float,
        confidence: float
    ) -> Tuple[int, float]:
        """
        Calculates dynamic volatility-adjusted & conviction-weighted capital allocation.
        Formula:
          Risk Capital (₹10,000) / Stop Distance % * (Confidence / 0.70)
        """
        total_equity = self.get_portfolio_value()
        risk_budget = total_equity * self.RISK_PER_TRADE_PCT

        # Distance to ML Stop
        stop_dist_pct = abs(current_price - ml_stop_price) / current_price
        stop_dist_pct = max(stop_dist_pct, 0.015)  # Floor at 1.5% to prevent explosive allocation

        # Sizing with conviction multiplier (0.65 to 1.0)
        conviction_mult = min(1.25, max(0.75, confidence / 0.70))
        target_capital = (risk_budget / stop_dist_pct) * conviction_mult

        # Hard caps scaled by conviction (10% for >=65% confidence, 7.5% for >=55%)
        cap_pct = 0.10 if confidence >= 0.65 else 0.075
        max_allowed_capital = total_equity * cap_pct
        allocated_capital = min(target_capital, max_allowed_capital, self.cash)

        if allocated_capital < (current_price * 1):
            return 0, 0.0  # Cannot afford even 1 share

        quantity = int(allocated_capital // current_price)
        final_capital = round(quantity * current_price, 2)

        return quantity, final_capital

    def open_position(
        self,
        symbol: str,
        current_price: float,
        ml_stop_price: float,
        ml_target_1: float,
        ml_target_2: float,
        confidence: float,
        trigger_reason: str = "ORB_VWAP_BREAKOUT"
    ) -> Optional[Position]:
        """Attempts to open a new paper trade subject to risk governance checks."""
        # 1. Circuit breaker check
        if self.circuit_breaker_tripped:
            logger.warning(f"Order REJECTED for {symbol}: Daily Circuit Breaker Active (-3% drawdown reached).")
            return None

        # 2. Existing position check
        if symbol in self.positions:
            logger.warning(f"Order REJECTED for {symbol}: Position already open.")
            return None

        # 3. Maximum concurrent positions check
        if len(self.positions) >= self.MAX_OPEN_POSITIONS:
            logger.warning(f"Order REJECTED for {symbol}: Max open positions ({self.MAX_OPEN_POSITIONS}) reached.")
            return None

        # 4. Position Sizing
        quantity, capital = self.calculate_position_size(symbol, current_price, ml_stop_price, confidence)
        if quantity <= 0:
            logger.warning(f"Order REJECTED for {symbol}: Insufficient capital or risk constraints.")
            return None

        # 5. Order Execution
        request = OrderRequest(
            symbol=symbol,
            direction=OrderDirection.BUY,
            quantity=quantity,
            requested_price=current_price,
            trigger_reason=trigger_reason,
            is_delivery=True
        )
        execution = self.order_engine.execute_order(request, current_tick_price=current_price)
        self._record_order(execution)
        
        # Deduct cash
        self.cash += execution.total_cash_impact  # negative impact debits cash

        # Create Position
        pos = Position(
            trade_id=execution.order_id,
            symbol=symbol,
            entry_time=datetime.now(timezone.utc).isoformat(),
            entry_price=execution.filled_price,
            quantity=quantity,
            current_price=execution.filled_price,
            ml_stop_price=ml_stop_price,
            ml_target_1=ml_target_1,
            ml_target_2=ml_target_2,
            allocated_capital=abs(execution.total_cash_impact),
            entry_frictions=execution.statutory_charges.total_statutory_charges,
            highest_price_seen=execution.filled_price
        )

        self.positions[symbol] = pos
        self._persist_state()

        logger.info(
            f"OPENED PAPER TRADE: {symbol} | Qty: {quantity} @ Rs.{pos.entry_price:.2f} | "
            f"Cap: Rs.{pos.allocated_capital:,.2f} | Stop: Rs.{ml_stop_price:.2f} | T1: Rs.{ml_target_1:.2f}"
        )
        return pos

    def update_market_price(self, symbol: str, current_price: float, exit_time: Optional[datetime] = None) -> Optional[TradeExitResult]:
        """
        Updates live tick price for an open position and evaluates dynamic exits:
          - Stop-Loss Hit (Model 3 P05 Floor)
          - Target 1 Hit (Model 3 P75: Book 50% profit, move stop to breakeven)
          - Target 2 Hit (Model 1 Q90 Runner)
        """
        pos = self.positions.get(symbol)
        if not pos:
            return None

        pos.current_price = current_price
        pos.highest_price_seen = max(pos.highest_price_seen, current_price)
        pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
        pos.unrealized_pnl_pct = ((current_price / pos.entry_price) - 1.0) * 100.0

        exit_t = exit_time or datetime.now(timezone.utc)

        # Check Target 1 (Book 35% Profit, let 65% runner ride)
        if not pos.partial_exit_done and current_price >= pos.ml_target_1:
            partial_qty = max(1, int(round(pos.quantity * 0.35)))
            if partial_qty < pos.quantity:
                logger.info(f"TARGET 1 HIT for {symbol}: Booking 35% profit on {partial_qty} shares at Rs.{current_price:.2f}!")
                # Execute partial sell
                req = OrderRequest(
                    symbol=symbol,
                    direction=OrderDirection.SELL,
                    quantity=partial_qty,
                    requested_price=current_price,
                    trigger_reason="P75_TARGET_1_HIT"
                )
                exec_partial = self.order_engine.execute_order(req, current_tick_price=current_price)
                self._record_order(exec_partial)
                self.cash += exec_partial.total_cash_impact

                # Record partial settlement to trade history
                entry_t = datetime.fromisoformat(pos.entry_time)
                prop_entry_frictions = pos.entry_frictions * (partial_qty / pos.quantity)
                pos.entry_frictions -= prop_entry_frictions

                partial_settlement = self.order_engine.calculate_trade_close(
                    trade_id=f"{pos.trade_id}_T1",
                    symbol=symbol,
                    entry_time=entry_t,
                    exit_time=exit_t,
                    entry_price=pos.entry_price,
                    exit_price=exec_partial.filled_price,
                    quantity=partial_qty,
                    entry_frictions=prop_entry_frictions,
                    exit_frictions=exec_partial.statutory_charges.total_statutory_charges,
                    exit_trigger="P75_TARGET_1_PARTIAL_EXIT"
                )
                self._record_trade_settlement(partial_settlement)

                # Update position
                pos.quantity -= partial_qty
                pos.partial_exit_done = True
                # Move stop to Entry Price (Guaranteed Risk-Free Breakeven)
                pos.ml_stop_price = max(pos.ml_stop_price, pos.entry_price)
                self._persist_state()

        # Dynamic Trailing Stop for Runner (Trails behind price once Target 1 is booked)
        if pos.partial_exit_done and pos.highest_price_seen > pos.entry_price:
            trailing_stop_level = round(pos.entry_price + (pos.highest_price_seen - pos.entry_price) * 0.60, 2)
            pos.ml_stop_price = max(pos.ml_stop_price, trailing_stop_level)

        # Check Stop-Loss Hit
        if current_price <= pos.ml_stop_price:
            trigger = "BREAKEVEN_STOP_HIT" if pos.partial_exit_done else "P05_STOP_LOSS_HIT"
            logger.warning(f"STOP HIT for {symbol} ({trigger}) at Rs.{current_price:.2f} (Stop was Rs.{pos.ml_stop_price:.2f})!")
            return self.close_position(symbol, current_price, exit_trigger=trigger, exit_time=exit_t)

        # Check Target 2 (Runner Target / Q90)
        if pos.partial_exit_done and current_price >= pos.ml_target_2:
            logger.info(f"RUNNER TARGET 2 HIT for {symbol} (Model 1 Q90) at Rs.{current_price:.2f}!")
            return self.close_position(symbol, current_price, exit_trigger="Q90_RUNNER_TARGET_HIT", exit_time=exit_t)

        return None

    def close_position(
        self, 
        symbol: str, 
        current_price: float, 
        exit_trigger: str = "MANUAL_EXIT",
        exit_time: Optional[datetime] = None
    ) -> Optional[TradeExitResult]:
        """Closes an open paper trade and records settlement into trade_history."""
        pos = self.positions.pop(symbol, None)
        if not pos:
            return None

        # Execute sell order
        request = OrderRequest(
            symbol=symbol,
            direction=OrderDirection.SELL,
            quantity=pos.quantity,
            requested_price=current_price,
            trigger_reason=exit_trigger,
            is_delivery=True
        )
        execution = self.order_engine.execute_order(request, current_tick_price=current_price)
        self._record_order(execution)
        self.cash += execution.total_cash_impact

        # Calculate final settlement with STCG/LTCG
        entry_time = datetime.fromisoformat(pos.entry_time)
        actual_exit_time = exit_time or datetime.now(timezone.utc)

        settlement = self.order_engine.calculate_trade_close(
            trade_id=pos.trade_id,
            symbol=symbol,
            entry_time=entry_time,
            exit_time=actual_exit_time,
            entry_price=pos.entry_price,
            exit_price=execution.filled_price,
            quantity=pos.quantity,
            entry_frictions=pos.entry_frictions,
            exit_frictions=execution.statutory_charges.total_statutory_charges,
            exit_trigger=exit_trigger
        )

        # Record to SQLite history
        self._record_trade_settlement(settlement)

        self._persist_state()
        self._check_circuit_breaker()

        logger.info(
            f"CLOSED PAPER TRADE: {symbol} | Net PnL: Rs.{settlement.net_pnl:+,.2f} ({settlement.net_pnl_pct:+.2f}%) | "
            f"Tax: Rs.{settlement.capital_gains_tax:.2f} ({settlement.tax_type}) | Trigger: {exit_trigger}"
        )
        return settlement

    def get_portfolio_value(self) -> float:
        """Total current equity = Cash + Current Market Value of Open Positions."""
        invested = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        total = self.cash + invested
        self.peak_portfolio_value = max(self.peak_portfolio_value, total)
        return round(total, 2)

    def _check_circuit_breaker(self):
        """Halts trading if daily portfolio drawdown reaches -3%."""
        current_value = self.get_portfolio_value()
        daily_pnl_pct = (current_value - self.day_start_portfolio_value) / self.day_start_portfolio_value
        if daily_pnl_pct <= self.DAILY_CIRCUIT_BREAKER_PCT:
            self.circuit_breaker_tripped = True
            logger.critical(
                f"PORTFOLIO CIRCUIT BREAKER TRIPPED! Daily drawdown is {daily_pnl_pct*100:.2f}%. "
                f"Halting all new trading for today."
            )

    def get_summary(self) -> PortfolioSummary:
        """Returns comprehensive portfolio scorecard."""
        current_val = self.get_portfolio_value()
        invested = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # Realized PnL from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(SUM(net_pnl), 0) FROM trade_history")
            realized_pnl = float(cursor.fetchone()[0])

        total_return_pct = ((current_val - self.initial_capital) / self.initial_capital) * 100.0
        mdd_pct = ((current_val - self.peak_portfolio_value) / self.peak_portfolio_value) * 100.0
        daily_pnl_pct = ((current_val - self.day_start_portfolio_value) / self.day_start_portfolio_value) * 100.0

        return PortfolioSummary(
            initial_capital=self.initial_capital,
            current_cash=round(self.cash, 2),
            invested_capital=round(invested, 2),
            total_portfolio_value=current_val,
            total_realized_pnl=round(realized_pnl, 2),
            total_unrealized_pnl=round(unrealized, 2),
            total_return_pct=round(total_return_pct, 2),
            open_positions_count=len(self.positions),
            max_drawdown_pct=round(mdd_pct, 2),
            daily_pnl_pct=round(daily_pnl_pct, 2),
            circuit_breaker_tripped=self.circuit_breaker_tripped
        )
