import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import polars as pl
import numpy as np

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.config.settings import settings
from src.models.data_splitter import DataSplitter
from src.execution.portfolio_manager import VirtualPortfolioManager
from src.execution.strategy_runner import AIStrategyRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("Phase5VaultSimulation")

def run_vault_simulation():
    logger.info("================================================================================")
    logger.info("   PHASE 5 VALIDATION AUDIT: 2-YEAR OUT-OF-SAMPLE TEST VAULT (2024 TO 2026)     ")
    logger.info("   Model Weights: models/validation/weights/ (Trained < Oct 2023, ZERO LEAKAGE) ")
    logger.info("   Virtual Capital: Rs.10,00,000 INR | Realistic Indian Taxes & 0.05% Slippage  ")
    logger.info("================================================================================")

    # 1. Load 2-Year Out-of-Sample Test Vault
    splitter = DataSplitter()
    logger.info("Loading 2-Year Test Vault data (Jan 2024 to Nov 2026)...")
    _, test_df0 = splitter.load_dataset(0, max_symbols=250, min_turnover_cr=0.5)
    
    # Filter strictly to Test Vault dates (2024 to 2026)
    test_df0 = test_df0.filter(pl.col("date") >= pl.date(2024, 1, 1)).sort("date")
    dates = test_df0["date"].unique().sort().to_list()
    logger.info(f"Loaded {len(test_df0):,} out-of-sample bars across {len(dates)} market sessions.")

    # 2. Boot Portfolio Manager with Rs.10,00,000 INR and Validation Models
    vault_db = BASE_DIR / "data" / "paper_trading" / "vault_test" / "vault_ledger.db"
    vault_db.parent.mkdir(parents=True, exist_ok=True)
    if vault_db.exists():
        vault_db.unlink()

    initial_capital = 1000000.0
    pm = VirtualPortfolioManager(initial_capital=initial_capital, db_path=vault_db)
    
    # Point AIStrategyRunner strictly to validation weights
    val_model_dir = BASE_DIR / "models" / "validation" / "weights"
    runner = AIStrategyRunner(portfolio_manager=pm, model_dir=val_model_dir)

    # 3. Step through weekly rebalance sessions across 2024-2026
    # To simulate realistic swing trading without running 2 million tick iterations:
    # Model 0 screens the top 5 focus candidates each weekly session (every 5th trading day)
    m0_features = runner.registry["models"]["model0"]["features"]

    weekly_dates = dates[::5]  # Every 5 market sessions
    logger.info(f"Simulating {len(weekly_dates)} multi-day trading cycles across the 2-Year Vault...")

    total_trades_count = 0
    target1_hits = 0
    target2_runner_hits = 0
    breakeven_hits = 0
    stop_loss_hits = 0

    portfolio_curve = []

    for d in weekly_dates:
        day_df = test_df0.filter(pl.col("date") == d)
        if len(day_df) < 10:
            continue

        # Screener
        candidates = runner.run_premarket_screener(day_df)
        top_candidates = candidates[:3]  # Top 3 highest conviction per cycle

        for c in top_candidates:
            if len(pm.positions) >= pm.MAX_OPEN_POSITIONS:
                break

            sym = c.symbol
            entry_px = c.current_price
            if entry_px <= 0 or sym in pm.positions:
                continue

            # Target & Stop Setup
            # P05 Stop Loss clamped at max -6.0%
            stop_px = round(entry_px * 0.94, 2)
            # P75 Target 1 at +6.5%
            target1_px = round(entry_px * 1.065, 2)
            # Q90 Target 2 at +15.0%
            target2_px = round(entry_px * 1.15, 2)

            # Open Position
            pos = pm.open_position(
                symbol=sym,
                current_price=entry_px,
                ml_stop_price=stop_px,
                ml_target_1=target1_px,
                ml_target_2=target2_px,
                confidence=0.72,
                trigger_reason="ORB_VWAP_BREAKOUT"
            )

            if not pos:
                continue

            total_trades_count += 1

            # Get forward outcome for this stock from test vault
            stock_data = day_df.filter(pl.col("symbol") == sym)
            fwd_ret = float(stock_data["target_fwd_ret_5d"].item(0)) if len(stock_data) > 0 and stock_data["target_fwd_ret_5d"].item(0) is not None else 0.0
            actual_fwd_pct = (np.exp(fwd_ret) - 1.0) * 100.0

            # Simulate outcome:
            if actual_fwd_pct >= 15.0:
                # Surged past Target 1 and Target 2
                runner.process_intraday_tick(sym, price=target1_px, volume=5000)
                pm.update_market_price(sym, current_price=target2_px)
                target1_hits += 1
                target2_runner_hits += 1
            elif actual_fwd_pct >= 6.5:
                # Hit Target 1 (book 50%), then pulled back to breakeven
                runner.process_intraday_tick(sym, price=target1_px, volume=5000)
                pm.update_market_price(sym, current_price=pos.ml_stop_price - 0.1)
                target1_hits += 1
                breakeven_hits += 1
            elif actual_fwd_pct <= -6.0:
                # Stopped out at -6.0% P05 floor
                pm.update_market_price(sym, current_price=stop_px)
                stop_loss_hits += 1
            else:
                # Exit at end of 5-day cycle with market return
                exit_px = round(entry_px * (1.0 + (actual_fwd_pct / 100.0)), 2)
                pm.close_position(sym, current_price=exit_px, exit_trigger="5D_CYCLE_CLOSE")

        val = pm.get_portfolio_value()
        portfolio_curve.append(val)

    # Calculate final metrics
    summary = pm.get_summary()
    equity_arr = np.array(portfolio_curve)
    peaks = np.maximum.accumulate(equity_arr)
    drawdowns = (equity_arr - peaks) / peaks
    max_drawdown = float(np.min(drawdowns)) * 100.0

    print("\n" + "=" * 80)
    print("      FINAL 2-YEAR OUT-OF-SAMPLE TEST VAULT RESULTS (2024 - 2026)")
    print("      Strictly Evaluated on Unseen Validation Models (Zero Leakage)")
    print("=" * 80)
    print(f"  * Starting Virtual Capital : Rs.{initial_capital:,.2f} INR")
    print(f"  * Ending Virtual Portfolio : Rs.{summary.total_portfolio_value:,.2f} INR")
    print(f"  * Total Net Realized Profit: Rs.{summary.total_realized_pnl:+,.2f} INR")
    print(f"  * Cumulative 2-Year Return : {summary.total_return_pct:+.2f}%")
    print(f"  * Maximum Portfolio Drawdown: {max_drawdown:.2f}%")
    print(f"  * Total Simulated Trades   : {total_trades_count}")
    print(f"    - Target 1 Hits (+6.5%)  : {target1_hits}")
    print(f"    - Target 2 Hits (+15.0%) : {target2_runner_hits}")
    print(f"    - Breakeven Exits (0.0%) : {breakeven_hits}")
    print(f"    - Stop-Loss Hits (-6.0%) : {stop_loss_hits}")
    print("=" * 80)

if __name__ == "__main__":
    run_vault_simulation()

