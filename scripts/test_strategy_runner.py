import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
import polars as pl
import numpy as np

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.execution.portfolio_manager import VirtualPortfolioManager
from src.execution.strategy_runner import AIStrategyRunner, IntradayBar

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TestStrategyRunner")

def test_strategy_runner():
    logger.info("Initializing VirtualPortfolioManager and AIStrategyRunner...")
    pm = VirtualPortfolioManager()
    runner = AIStrategyRunner(portfolio_manager=pm)

    logger.info("Verifying model registry & loaded models...")
    assert "model0" in runner.models
    assert "model1" in runner.models
    assert "model2" in runner.models
    assert "model3" in runner.models
    assert "model4" in runner.models

    # Create dummy universe of 15 stocks with features
    symbols = [f"STOCK_{i}" for i in range(15)]
    np.random.seed(42)
    m0_features = runner.registry["models"]["model0"]["features"]
    
    data = {"symbol": symbols, "close": [100.0 + i * 20.0 for i in range(15)]}
    for feat in m0_features:
        data[feat] = np.random.randn(15).tolist()

    df_screener = pl.DataFrame(data)

    # Dummy macro gatekeeper dataframe
    df_macro = pl.DataFrame({
        "symbol": symbols,
        "max_drawdown_756d": [-0.15] * 14 + [-0.55], # STOCK_14 is structurally broken
        "calmar_ratio_3y": [1.5] * 14 + [-0.2]
    })

    logger.info("Testing Pre-Market Screener (Tier 0 & Tier 1)...")
    watchlist = runner.run_premarket_screener(df_screener, df_macro)
    assert len(watchlist) > 0
    # STOCK_14 must be filtered out by macro gatekeeper
    banned_in_watchlist = [c.symbol for c in watchlist if c.symbol == "STOCK_14"]
    assert len(banned_in_watchlist) == 0, "Banned stock passed through macro gatekeeper!"
    logger.info(f"Screener returned {len(watchlist)} candidates. Top candidate: {watchlist[0].symbol}")

    # Test Corridor & Action Evaluation (Tier 2 & Tier 3)
    top_sym = watchlist[0].symbol
    top_px = watchlist[0].current_price
    m3_features = {k: 0.05 for k in runner.registry["models"]["model3"]["features"]}
    m4_features = {k: 0.1 for k in runner.registry["models"]["model4"]["features"]}
    m1_features = {k: 0.08 for k in runner.registry["models"]["model1"]["features"]}
    combined_feats = {**m3_features, **m4_features, **m1_features}

    decision = runner.evaluate_corridor_and_action(top_sym, top_px, combined_feats)
    logger.info(f"Signal Decision for {top_sym}: Action={decision.action}, Conf={decision.confidence:.2%}, Approved={decision.is_approved}")
    logger.info(f"Levels: Price={decision.current_price:.2f}, Stop={decision.ml_stop_price:.2f}, T1={decision.ml_target_1:.2f}, T2={decision.ml_target_2:.2f}")

    # Manually approve signal for trigger test
    decision.is_approved = True
    runner.approved_signals[top_sym] = decision

    # Test ORB Window (09:15 - 09:30 AM)
    runner.register_orb_candle(IntradayBar(
        timestamp=datetime.now(timezone.utc),
        symbol=top_sym,
        open=top_px,
        high=top_px + 2.0,
        low=top_px - 1.0,
        close=top_px + 1.0,
        volume=1000.0
    ), is_orb_window=True)

    # Test Tier 4 Breakout Trigger
    breakout_px = top_px + 3.0  # Above ORB High (top_px + 2.0)
    logger.info(f"Sending breakout tick at Rs.{breakout_px:.2f} (above ORB high)...")
    pos = runner.process_intraday_tick(top_sym, price=breakout_px, volume=2000.0, rvol=1.5)
    assert pos is not None, "Position should have been opened on breakout!"
    assert top_sym in pm.positions, "Position should be in PortfolioManager"
    logger.info(f"Position successfully opened! Qty={pos.quantity}, Entry={pos.entry_price:.2f}")

    # Test Target 1 Hit (Model 3 P75 -> Books 50%, moves stop to breakeven)
    initial_qty = pos.quantity
    t1_px = pos.ml_target_1 + 1.0
    logger.info(f"Simulating price jump to Target 1 at Rs.{t1_px:.2f}...")
    runner.process_intraday_tick(top_sym, price=t1_px, volume=500.0)
    assert pos.partial_exit_done is True, "Target 1 partial exit should be done"
    assert pos.quantity == initial_qty - (initial_qty // 2), "Quantity should be reduced by 50%"
    assert pos.ml_stop_price >= pos.entry_price, "Stop-loss must be moved to entry (Breakeven)"
    logger.info("Target 1 verified! 50% booked, stop raised to breakeven.")

    # Test Target 2 Hit (Model 1 Q90 Runner)
    t2_px = pos.ml_target_2 + 2.0
    logger.info(f"Simulating price surge to Runner Target 2 at Rs.{t2_px:.2f}...")
    runner.process_intraday_tick(top_sym, price=t2_px, volume=500.0)
    assert top_sym not in pm.positions, "Position should be closed at Target 2"
    logger.info("Target 2 verified! Trade fully closed with profits.")

    summary = pm.get_summary()
    logger.info(f"Final Portfolio Summary: Realized PnL: Rs.{summary.total_realized_pnl:+,.2f}, Return: {summary.total_return_pct:+.2f}%")
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_strategy_runner()
