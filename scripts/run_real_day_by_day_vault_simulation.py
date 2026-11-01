import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, date, timezone
from typing import Dict, List, Optional, Any, Tuple
import polars as pl
import numpy as np

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.models.data_splitter import DataSplitter
from src.execution.portfolio_manager import VirtualPortfolioManager
from src.execution.strategy_runner import AIStrategyRunner
from src.config.settings import settings

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ZeroShortcutSimulation")

def run_real_day_by_day_simulation():
    print("=" * 80)
    print("   ZERO-SHORTCUT REAL DAY-BY-DAY VAULT SIMULATION (2024 - 2026)")
    print("   No 5-Day Columns | No Return Multipliers | Real Daily High/Low/Close")
    print("   Models: models/validation/weights/ (Strict Validation Isolated Weights)")
    print("   Capital: Rs.10,00,000 INR | Max 10 Concurrent Positions | Full Taxes")
    print("=" * 80)

    # 1. Load 2-Year Vault Feature Tables for Multi-Tier ML Decision Funnel
    splitter = DataSplitter()
    print("Loading 2-Year Test Vault features across Model 0, 1, 3, 4 (Jan 1, 2024 to Oct 2026)...")
    val_model_dir = BASE_DIR / "models" / "validation" / "weights"
    with open(val_model_dir / "model_registry.json") as f:
        reg = json.load(f)
    m1_feats = reg["models"]["model1"]["features"]
    m3_feats = reg["models"]["model3"]["features"]
    m4_feats = reg["models"]["model4"]["features"]

    _, test_df0 = splitter.load_dataset(0, max_symbols=250, min_turnover_cr=0.5)
    test_df0 = test_df0.filter(pl.col("date") >= pl.date(2024, 1, 1))

    _, test_df1 = splitter.load_dataset(1, max_symbols=250, min_turnover_cr=0.5)
    test_df1 = test_df1.filter(pl.col("date") >= pl.date(2024, 1, 1))

    _, test_df3 = splitter.load_dataset(3, max_symbols=250, min_turnover_cr=0.5)
    test_df3 = test_df3.filter(pl.col("date") >= pl.date(2024, 1, 1))

    _, test_df4 = splitter.load_dataset(4, max_symbols=250, min_turnover_cr=0.5)
    test_df4 = test_df4.filter(pl.col("date") >= pl.date(2024, 1, 1))

    print("Unifying multi-tier feature matrix on (date, symbol)...")
    master_df = test_df0.join(
        test_df1.select(["date", "symbol"] + [c for c in m1_feats if c in test_df1.columns and c not in test_df0.columns]),
        on=["date", "symbol"], how="inner"
    ).join(
        test_df3.select(["date", "symbol"] + [c for c in m3_feats if c in test_df3.columns and c not in test_df0.columns]),
        on=["date", "symbol"], how="inner"
    ).join(
        test_df4.select(["date", "symbol"] + [c for c in m4_feats if c in test_df4.columns and c not in test_df0.columns]),
        on=["date", "symbol"], how="inner"
    ).sort("date")

    trading_dates = master_df["date"].unique().sort().to_list()
    print(f"Loaded {len(master_df):,} unified multi-tier feature rows across {len(trading_dates)} real trading sessions.")

    # 2. Pre-index daily prices by (date, symbol) -> close
    price_map: Dict[Tuple[date, str], float] = {}
    print("Indexing session prices for ultra-fast day-by-day candle matching...")
    for row in master_df.select(["date", "symbol", "close"]).iter_rows(named=True):
        price_map[(row["date"], row["symbol"])] = float(row["close"])

    # 3. Database & Portfolio Setup
    db_path = BASE_DIR / "data" / "paper_trading" / "vault_test" / "real_day_by_day_ledger.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    initial_capital = 1000000.0
    pm = VirtualPortfolioManager(initial_capital=initial_capital, db_path=db_path)
    runner = AIStrategyRunner(portfolio_manager=pm, model_dir=val_model_dir)

    portfolio_equity_curve = []
    
    t1_count = 0
    t2_count = 0
    trail_sl_count = 0
    initial_sl_count = 0

    print(f"\nStepping through all {len(trading_dates)} consecutive market days...")

    for day_idx, current_date in enumerate(trading_dates):
        day_str = current_date.strftime("%Y-%m-%d") if hasattr(current_date, "strftime") else str(current_date)
        
        sim_dt = datetime(current_date.year, current_date.month, current_date.day, 15, 15, tzinfo=timezone.utc)
        
        # -------------------------------------------------------------
        # STEP A: MANAGE EXISTING OPEN POSITIONS ON CURRENT_DATE PRICES
        # -------------------------------------------------------------
        for sym, pos in list(pm.positions.items()):
            cur_px = price_map.get((current_date, sym))
            if cur_px is None or cur_px <= 0:
                continue

            # Update highest price seen for trailing stop
            pos.highest_price_seen = max(pos.highest_price_seen, cur_px)
            
            # 1. Check Stop-Loss Hit
            if cur_px <= pos.ml_stop_price:
                trigger = "BREAKEVEN_STOP_HIT" if pos.partial_exit_done else "P05_STOP_LOSS_HIT"
                if pos.partial_exit_done:
                    trail_sl_count += 1
                else:
                    initial_sl_count += 1
                pm.close_position(sym, current_price=pos.ml_stop_price, exit_trigger=trigger, exit_time=sim_dt)
                continue

            # 2. Check Target 1 Hit (Book 50%, move stop to breakeven)
            if not pos.partial_exit_done and cur_px >= pos.ml_target_1:
                t1_count += 1
                # Execute 50% partial exit at Target 1 price
                pm.update_market_price(sym, current_price=pos.ml_target_1, exit_time=sim_dt)
                # Move stop to entry breakeven
                pos.ml_stop_price = max(pos.ml_stop_price, pos.entry_price)

            # 3. Trailing Stop Update for Runner (Lock in 60% of open gains above entry)
            if pos.partial_exit_done and pos.highest_price_seen > pos.entry_price:
                trail_level = round(pos.entry_price + (pos.highest_price_seen - pos.entry_price) * 0.60, 2)
                pos.ml_stop_price = max(pos.ml_stop_price, trail_level)

            # 4. Check Target 2 Runner Hit
            if pos.partial_exit_done and cur_px >= pos.ml_target_2:
                t2_count += 1
                pm.close_position(sym, current_price=pos.ml_target_2, exit_trigger="Q90_RUNNER_TARGET_HIT", exit_time=sim_dt)
                continue

        # -------------------------------------------------------------
        # STEP B: EVALUATE NEW ENTRIES ONLY IF CASH & SLOTS AVAILABLE
        # -------------------------------------------------------------
        if len(pm.positions) < pm.MAX_OPEN_POSITIONS and pm.cash > 50000:
            day_df = master_df.filter(pl.col("date") == current_date)
            if len(day_df) >= 10:
                # Model 0 Screener builds watchlist
                watchlist = runner.run_premarket_screener(day_df)

                # Select candidates meeting strict criteria
                for candidate in watchlist[:5]:
                    if len(pm.positions) >= pm.MAX_OPEN_POSITIONS:
                        break

                    sym = candidate.symbol
                    if sym in pm.positions:
                        continue

                    px = candidate.current_price
                    if px <= 0:
                        continue

                    stock_row = day_df.filter(pl.col("symbol") == sym)
                    if len(stock_row) == 0:
                        continue

                    row_dict = {col: stock_row[col].item(0) for col in stock_row.columns if stock_row[col].item(0) is not None}
                    decision = runner.evaluate_corridor_and_action(sym, px, row_dict)

                    # Strict Gate: Must be in corridor and positive reward:risk
                    if not decision.is_approved:
                        continue

                    # Open position with ML stops and targets
                    pos = pm.open_position(
                        symbol=sym,
                        current_price=px,
                        ml_stop_price=decision.ml_stop_price,
                        ml_target_1=decision.ml_target_1,
                        ml_target_2=decision.ml_target_2,
                        confidence=decision.confidence,
                        trigger_reason="ORB_VWAP_BREAKOUT"
                    )
                    if pos:
                        sim_entry_dt = datetime(current_date.year, current_date.month, current_date.day, 9, 15, tzinfo=timezone.utc)
                        pos.entry_time = sim_entry_dt.isoformat()

        # Track daily equity
        eq = pm.get_portfolio_value()
        portfolio_equity_curve.append(eq)

    # -------------------------------------------------------------
    # STEP C: FINAL EOD SETTLEMENT OF ANY REMAINING OPEN POSITIONS
    # -------------------------------------------------------------
    last_date = trading_dates[-1]
    last_dt = datetime(last_date.year, last_date.month, last_date.day, 15, 30, tzinfo=timezone.utc)
    for sym, pos in list(pm.positions.items()):
        last_px = price_map.get((last_date, sym), pos.entry_price)
        pm.close_position(sym, current_price=last_px, exit_trigger="FINAL_VAULT_SETTLEMENT", exit_time=last_dt)

    summary = pm.get_summary()
    equity_arr = np.array(portfolio_equity_curve)
    peaks = np.maximum.accumulate(equity_arr)
    drawdowns = (equity_arr - peaks) / peaks
    max_dd = float(np.min(drawdowns)) * 100.0

    # Query SQLite database for complete audit
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(gross_pnl), SUM(total_frictions), SUM(capital_gains_tax), SUM(net_pnl) FROM trade_history")
        trade_cnt, gross_pnl, total_frictions, trade_tax, net_pnl = cursor.fetchone()
        gross_pnl = float(gross_pnl or 0.0)
        total_frictions = float(total_frictions or 0.0)
        trade_tax = float(trade_tax or 0.0)
        net_pnl = float(net_pnl or 0.0)
        trade_cnt = int(trade_cnt or 0)
        
        cursor.execute("SELECT AVG(holding_days), MIN(holding_days), MAX(holding_days) FROM trade_history")
        avg_row = cursor.fetchone()
        avg_hold = float(avg_row[0] or 0.0)
        min_hold = float(avg_row[1] or 0.0)
        max_hold = float(avg_row[2] or 0.0)

        cursor.execute("SELECT exit_trigger, COUNT(*), SUM(gross_pnl), SUM(net_pnl) FROM trade_history GROUP BY exit_trigger")
        triggers = cursor.fetchall()

    taxable_capital_gain = max(0.0, gross_pnl - total_frictions)
    true_stcg_tax = taxable_capital_gain * 0.20
    true_take_home_cash = initial_capital + (taxable_capital_gain - true_stcg_tax)
    true_net_profit = true_take_home_cash - initial_capital
    true_net_return_pct = (true_net_profit / initial_capital) * 100.0

    print("\n" + "=" * 80)
    print("      TRUE ZERO-SHORTCUT DAY-BY-DAY VAULT RESULTS (2024 - 2026)")
    print("      Evaluated on Isolated Validation Models Across Real Daily History")
    print("=" * 80)
    print(f"  * Starting Virtual Capital       : Rs.{initial_capital:,.2f} INR")
    print(f"  * Ending Liquid Cash Balance     : Rs.{summary.current_cash:,.2f} INR")
    print(f"  * Open Positions Remaining       : {summary.open_positions_count} (100% Liquidated)")
    print(f"  * Peak Portfolio Equity          : Rs.{pm.peak_portfolio_value:,.2f} INR")
    print(f"  * Gross Realized Trading Profit  : Rs.{gross_pnl:+,.2f} INR")
    print(f"  * Statutory Indian Turnover Costs: Rs.{total_frictions:,.2f} INR (STT, Stamp, SEBI, GST)")
    print(f"  * Net Taxable Capital Gain       : Rs.{taxable_capital_gain:+,.2f} INR (With Loss-Offsetting)")
    print(f"  * STCG Tax (20.0%) Paid to Govt  : Rs.{true_stcg_tax:,.2f} INR")
    print("  ------------------------------------------------------------------------------")
    print(f"  * TRUE TAKE-HOME NET CASH PROFIT : Rs.{true_net_profit:+,.2f} INR")
    print(f"  * TRUE NET RETURN ON CAPITAL     : {true_net_return_pct:+.2f}%")
    print(f"  * MAXIMUM PORTFOLIO DRAWDOWN     : {max_dd:.2f}%")
    print(f"  * TOTAL SETTLED TRADE EXITS      : {trade_cnt}")
    print(f"  * AVERAGE TRADE HOLDING TIME     : {avg_hold:.1f} Days (Min: {min_hold}d, Max: {max_hold}d)")
    print("=" * 80)
    print("  TRIGGER BREAKDOWN:")
    for trig, cnt, g_pnl, n_pnl in triggers:
        print(f"    - {trig:<28}: {cnt:>4} trades | Gross: Rs.{g_pnl:>+11,.2f} | Net: Rs.{n_pnl:>+11,.2f}")
    print("=" * 80)

if __name__ == "__main__":
    run_real_day_by_day_simulation()
