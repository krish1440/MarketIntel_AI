import sqlite3
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_services, ServiceContainer
from src.api.schemas.trading import (
    PortfolioSummaryResponse,
    PositionItem,
    TradeItem,
    ManualOrderRequest
)

logger = logging.getLogger("TradingRoute")
router = APIRouter(prefix="/api/trading", tags=["Trading & Portfolio"])


@router.get("/portfolio", response_model=PortfolioSummaryResponse)
def get_portfolio_summary(services: ServiceContainer = Depends(get_services)):
    """
    Returns high-level institutional portfolio scorecard:
    Capital, Total Value, Realized / Unrealized P&L, Daily P&L, and Circuit Breaker state.
    """
    pm = services.portfolio_manager
    # Update current position prices from Redis live cache
    for sym, pos in pm.positions.items():
        quote = services.redis_manager.get_live_quote(sym)
        if quote and "close" in quote:
            cur_price = float(quote["close"])
            if cur_price > 0:
                pos.current_price = cur_price
                pos.highest_price_seen = max(pos.highest_price_seen, cur_price)
                pos.unrealized_pnl = round((cur_price - pos.entry_price) * pos.quantity, 2)
                pos.unrealized_pnl_pct = round(((cur_price / pos.entry_price) - 1.0) * 100.0, 2)

    summary = pm.get_summary()
    return PortfolioSummaryResponse(
        initial_capital=summary.initial_capital,
        current_cash=summary.current_cash,
        total_portfolio_value=summary.total_portfolio_value,
        total_invested=summary.invested_capital,
        total_unrealized_pnl=summary.total_unrealized_pnl,
        total_realized_pnl=summary.total_realized_pnl,
        total_return_pct=summary.total_return_pct,
        open_positions_count=summary.open_positions_count,
        max_drawdown_pct=summary.max_drawdown_pct,
        daily_pnl_pct=summary.daily_pnl_pct,
        circuit_breaker_tripped=summary.circuit_breaker_tripped
    )


@router.get("/positions", response_model=List[PositionItem])
def get_active_positions(services: ServiceContainer = Depends(get_services)):
    """
    Returns list of all currently active paper trading positions with live unrealized P&L.
    """
    pm = services.portfolio_manager
    items: List[PositionItem] = []

    for sym, pos in pm.positions.items():
        # Live mark-to-market
        quote = services.redis_manager.get_live_quote(sym)
        cur_price = pos.current_price
        if quote and "close" in quote:
            cp = float(quote["close"])
            if cp > 0:
                cur_price = cp
                pos.current_price = cur_price
                pos.highest_price_seen = max(pos.highest_price_seen, cur_price)
                pos.unrealized_pnl = round((cur_price - pos.entry_price) * pos.quantity, 2)
                pos.unrealized_pnl_pct = round(((cur_price / pos.entry_price) - 1.0) * 100.0, 2)

        items.append(PositionItem(
            symbol=pos.symbol,
            trade_id=pos.trade_id,
            entry_time=pos.entry_time,
            entry_price=round(pos.entry_price, 2),
            quantity=pos.quantity,
            current_price=round(cur_price, 2),
            allocated_capital=round(pos.allocated_capital, 2),
            unrealized_pnl=round(pos.unrealized_pnl, 2),
            unrealized_pnl_pct=round(pos.unrealized_pnl_pct, 2),
            ml_stop_price=round(pos.ml_stop_price, 2),
            ml_target_1=round(pos.ml_target_1, 2),
            ml_target_2=round(pos.ml_target_2, 2),
            partial_exit_done=pos.partial_exit_done,
            highest_price_seen=round(pos.highest_price_seen, 2)
        ))

    return items


@router.get("/trades", response_model=List[TradeItem])
def get_trade_history(
    limit: int = Query(50, ge=1, le=500),
    services: ServiceContainer = Depends(get_services)
):
    """
    Returns closed trade audit log with statutory friction breakdown and capital gains tax.
    """
    pm = services.portfolio_manager
    trades: List[TradeItem] = []

    if not pm.db_path.exists():
        return trades

    try:
        with sqlite3.connect(pm.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    trade_id, symbol, entry_time, exit_time, holding_days, quantity,
                    entry_price, exit_price, gross_pnl, gross_pnl_pct, total_frictions,
                    capital_gains_tax, tax_type, net_pnl, net_pnl_pct, exit_trigger
                FROM trade_history
                ORDER BY exit_time DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

            for r in rows:
                trades.append(TradeItem(
                    trade_id=r["trade_id"],
                    symbol=r["symbol"],
                    entry_time=r["entry_time"],
                    exit_time=r["exit_time"],
                    holding_days=int(r["holding_days"]),
                    quantity=int(r["quantity"]),
                    entry_price=round(float(r["entry_price"]), 2),
                    exit_price=round(float(r["exit_price"]), 2),
                    gross_pnl=round(float(r["gross_pnl"]), 2),
                    gross_pnl_pct=round(float(r["gross_pnl_pct"]), 2),
                    total_transaction_frictions=round(float(r["total_frictions"]), 2),
                    capital_gains_tax=round(float(r["capital_gains_tax"]), 2),
                    tax_type=r["tax_type"],
                    net_pnl=round(float(r["net_pnl"]), 2),
                    net_pnl_pct=round(float(r["net_pnl_pct"]), 2),
                    exit_trigger=r["exit_trigger"]
                ))
    except Exception as e:
        logger.error(f"Error querying trade_history: {e}")

    return trades


@router.post("/order")
def place_order(
    order: ManualOrderRequest,
    services: ServiceContainer = Depends(get_services)
):
    """
    Places manual simulated paper trade with statutory friction & risk governance.
    """
    pm = services.portfolio_manager
    symbol = order.symbol.upper().strip()
    direction = order.direction.upper().strip()

    if direction not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Direction must be BUY or SELL")

    # Determine execution price
    price = order.price
    if not price or price <= 0:
        quote = services.redis_manager.get_live_quote(symbol)
        if quote and "close" in quote and float(quote["close"]) > 0:
            price = float(quote["close"])
        else:
            # Fallback to chart service
            candles = services.chart_service.get_candlesticks(symbol, timeframe="1d", limit=2)
            if candles:
                price = float(candles[-1]["close"])
            else:
                raise HTTPException(status_code=404, detail=f"No live or historical price found for {symbol}")

    if direction == "BUY":
        # Check circuit breaker
        if pm.circuit_breaker_tripped:
            raise HTTPException(status_code=403, detail="Trading halted: Daily portfolio circuit breaker active (-3% drawdown)")

        if symbol in pm.positions:
            raise HTTPException(status_code=400, detail=f"Position already open for {symbol}")

        if len(pm.positions) >= pm.MAX_OPEN_POSITIONS:
            raise HTTPException(status_code=400, detail=f"Max concurrent positions ({pm.MAX_OPEN_POSITIONS}) reached")

        # Try to query Model 3 corridor for intelligent stop/target
        ml_stop = round(price * 0.98, 2)
        ml_t1 = round(price * 1.04, 2)
        ml_t2 = round(price * 1.08, 2)
        confidence = 0.70

        pos = pm.open_position(
            symbol=symbol,
            current_price=price,
            ml_stop_price=ml_stop,
            ml_target_1=ml_t1,
            ml_target_2=ml_t2,
            confidence=confidence,
            trigger_reason="MANUAL_ORDER"
        )
        if not pos:
            raise HTTPException(status_code=400, detail="Order rejected by risk management (insufficient cash or capital limits)")

        return {
            "status": "FILLED",
            "symbol": pos.symbol,
            "trade_id": pos.trade_id,
            "direction": "BUY",
            "quantity": pos.quantity,
            "filled_price": pos.entry_price,
            "allocated_capital": pos.allocated_capital,
            "ml_stop_price": pos.ml_stop_price,
            "ml_target_1": pos.ml_target_1
        }

    else: # SELL
        if symbol not in pm.positions:
            raise HTTPException(status_code=404, detail=f"No active position to sell for {symbol}")

        settlement = pm.close_position(symbol, current_price=price, exit_trigger="MANUAL_SELL")
        if not settlement:
            raise HTTPException(status_code=500, detail="Failed to close position")

        return {
            "status": "FILLED",
            "symbol": settlement.symbol,
            "trade_id": settlement.trade_id,
            "direction": "SELL",
            "quantity": settlement.quantity,
            "entry_price": settlement.entry_price,
            "exit_price": settlement.exit_price,
            "gross_pnl": settlement.gross_pnl,
            "statutory_charges": settlement.total_transaction_frictions,
            "capital_gains_tax": settlement.capital_gains_tax,
            "net_pnl": settlement.net_pnl,
            "net_pnl_pct": settlement.net_pnl_pct
        }


@router.post("/close/{symbol}")
def close_position(
    symbol: str,
    services: ServiceContainer = Depends(get_services)
):
    """
    Directly squares off an open position for `symbol` at current market price.
    """
    sym = symbol.upper().strip()
    pm = services.portfolio_manager

    if sym not in pm.positions:
        raise HTTPException(status_code=404, detail=f"No active position found for {sym}")

    # Get market price
    quote = services.redis_manager.get_live_quote(sym)
    price = None
    if quote and "close" in quote and float(quote["close"]) > 0:
        price = float(quote["close"])
    else:
        candles = services.chart_service.get_candlesticks(sym, timeframe="1d", limit=2)
        if candles:
            price = float(candles[-1]["close"])
        else:
            price = pm.positions[sym].current_price

    settlement = pm.close_position(sym, current_price=price, exit_trigger="MANUAL_SQUARE_OFF")
    if not settlement:
        raise HTTPException(status_code=500, detail="Failed to close position")

    return {
        "status": "CLOSED",
        "symbol": sym,
        "trade_id": settlement.trade_id,
        "quantity": settlement.quantity,
        "entry_price": settlement.entry_price,
        "exit_price": settlement.exit_price,
        "gross_pnl": settlement.gross_pnl,
        "net_pnl": settlement.net_pnl,
        "net_pnl_pct": settlement.net_pnl_pct,
        "exit_trigger": settlement.exit_trigger
    }
