import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone
from src.execution.order_engine import SimulatedOrderEngine, OrderRequest, OrderDirection

def test_engine():
    engine = SimulatedOrderEngine()

    # Test 1: Market Buy execution
    req_buy = OrderRequest(
        symbol="RELIANCE",
        direction=OrderDirection.BUY,
        quantity=50,
        requested_price=1000.0,
        trigger_reason="ORB_VWAP_BREAKOUT"
    )
    exec_buy = engine.execute_order(req_buy, current_tick_price=1000.0)
    print("Buy Execution:")
    print(f"  Filled Price: Rs.{exec_buy.filled_price:.2f} (Slippage: Rs.{exec_buy.slippage_cost:.2f})")
    print(f"  Statutory Taxes: Rs.{exec_buy.statutory_charges.total_statutory_charges:.2f}")
    print(f"  Total Cash Impact: Rs.{exec_buy.total_cash_impact:.2f}")

    # Test 2: Short-Term Sell (Holding 21 Days -> STCG 20%)
    t_entry = datetime.now(timezone.utc) - timedelta(days=21)
    t_exit = datetime.now(timezone.utc)
    req_sell = OrderRequest(
        symbol="RELIANCE",
        direction=OrderDirection.SELL,
        quantity=50,
        requested_price=1100.0,
        trigger_reason="P75_TARGET_HIT"
    )
    exec_sell = engine.execute_order(req_sell, current_tick_price=1100.0)

    settlement_stcg = engine.calculate_trade_close(
        trade_id="trade_test_1",
        symbol="RELIANCE",
        entry_time=t_entry,
        exit_time=t_exit,
        entry_price=exec_buy.filled_price,
        exit_price=exec_sell.filled_price,
        quantity=50,
        entry_frictions=exec_buy.statutory_charges.total_statutory_charges,
        exit_frictions=exec_sell.statutory_charges.total_statutory_charges,
        exit_trigger="P75_TARGET_HIT"
    )

    print("\nShort-Term Trade Settlement (<365 Days):")
    print(f"  Holding Days: {settlement_stcg.holding_days}")
    print(f"  Gross PnL: Rs.{settlement_stcg.gross_pnl:.2f} ({settlement_stcg.gross_pnl_pct:+.2f}%)")
    print(f"  Transaction Frictions: Rs.{settlement_stcg.total_transaction_frictions:.2f}")
    print(f"  Capital Gains Tax: Rs.{settlement_stcg.capital_gains_tax:.2f} ({settlement_stcg.tax_type})")
    print(f"  Net PnL: Rs.{settlement_stcg.net_pnl:.2f} ({settlement_stcg.net_pnl_pct:+.2f}%)")

    # Test 3: Long-Term Sell (Holding 400 Days -> LTCG 12.5%)
    t_entry_lt = datetime.now(timezone.utc) - timedelta(days=400)
    settlement_ltcg = engine.calculate_trade_close(
        trade_id="trade_test_2",
        symbol="RELIANCE",
        entry_time=t_entry_lt,
        exit_time=t_exit,
        entry_price=exec_buy.filled_price,
        exit_price=1300.0,
        quantity=50,
        entry_frictions=exec_buy.statutory_charges.total_statutory_charges,
        exit_frictions=exec_sell.statutory_charges.total_statutory_charges,
        exit_trigger="MODEL2_REBALANCE"
    )
    print("\nLong-Term Trade Settlement (>365 Days):")
    print(f"  Holding Days: {settlement_ltcg.holding_days}")
    print(f"  Gross PnL: Rs.{settlement_ltcg.gross_pnl:.2f} ({settlement_ltcg.gross_pnl_pct:+.2f}%)")
    print(f"  Capital Gains Tax: Rs.{settlement_ltcg.capital_gains_tax:.2f} ({settlement_ltcg.tax_type})")
    print(f"  Net PnL: Rs.{settlement_ltcg.net_pnl:.2f} ({settlement_ltcg.net_pnl_pct:+.2f}%)")

if __name__ == "__main__":
    test_engine()
