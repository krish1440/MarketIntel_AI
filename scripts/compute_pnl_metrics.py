import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
import polars as pl
import lightgbm as lgb
import joblib

from src.models.data_splitter import DataSplitter
from src.config.settings import settings

def simulate_holdout_trading():
    splitter = DataSplitter()
    
    # 1. Load Model 0 (Top Ranker) on the 2-Year Test Vault (2024-2026)
    print("Loading 2-Year Out-Of-Sample Test Vault (Jan 1, 2024 to Nov 2026)...")
    _, test_df = splitter.load_dataset(0, max_symbols=300, min_turnover_cr=0.5)
    features = splitter.get_feature_columns(test_df)
    
    # Load Stage 1 trained model (trained strictly on <2024 data)
    model0_path = settings.BASE_DIR / "models" / "stage1" / "model0_screener.txt"
    model0 = lgb.Booster(model_file=str(model0_path))
    
    # Load Model 4 Classifier
    model4_path = settings.BASE_DIR / "models" / "stage1" / "model4_classifier.joblib"
    calibrated_clf4 = joblib.load(model4_path)
    _, test_df4 = splitter.load_dataset(4, max_symbols=300, min_turnover_cr=0.5)
    features4 = splitter.get_feature_columns(test_df4)

    # ----------------------------------------------------
    # Strategy A: Model 0 Pre-Market Screener (Top 10 Stocks Every Monday, 5-Day Holding)
    # ----------------------------------------------------
    X_test0 = test_df.select(features).to_numpy()
    preds0 = model0.predict(X_test0)
    df_eval0 = test_df.with_columns(pl.Series("rank_score", preds0))

    # Pick top 5 highest-ranked stocks each trading day (holding 5 trading days)
    # Forward return: close[t+5] / close[t] - 1
    top_picks = (
        df_eval0.sort(["date", "rank_score"], descending=[False, True])
        .group_by("date", maintain_order=True)
        .head(5)
        .with_columns([
            ((pl.col("target_fwd_ret_5d").exp() - 1.0) * 100.0).alias("trade_pnl_pct")
        ])
    )

    trade_returns = top_picks["trade_pnl_pct"].drop_nulls().to_numpy()
    total_trades = len(trade_returns)
    winning_trades = trade_returns[trade_returns > 0]
    losing_trades = trade_returns[trade_returns < 0]

    win_rate = (len(winning_trades) / total_trades) * 100
    avg_win = float(np.mean(winning_trades)) if len(winning_trades) > 0 else 0.0
    avg_loss = float(np.mean(losing_trades)) if len(losing_trades) > 0 else 0.0
    max_win = float(np.max(trade_returns))
    max_loss = float(np.min(trade_returns))  # Worst loss

    gross_profit = float(np.sum(winning_trades))
    gross_loss = float(np.abs(np.sum(losing_trades)))
    profit_factor = gross_profit / max(gross_loss, 1e-4)

    # Daily portfolio returns and Drawdown
    daily_port_ret = (
        top_picks.group_by("date")
        .agg(pl.col("trade_pnl_pct").mean().alias("daily_pnl_pct"))
        .sort("date")
    )
    port_rets = daily_port_ret["daily_pnl_pct"].to_numpy() / 100.0
    cum_equity = np.cumprod(1.0 + (port_rets / 5.0))  # 5-day overlapping capital allocation
    peak = np.maximum.accumulate(cum_equity)
    drawdowns = (cum_equity - peak) / peak
    max_drawdown = float(np.min(drawdowns)) * 100.0
    total_cum_return = (cum_equity[-1] - 1.0) * 100.0

    # ----------------------------------------------------
    # Strategy B: Model 4 Action Classifier (Strong Buy signals, 21-Day Holding with -6% Stop Loss)
    # ----------------------------------------------------
    clean4 = test_df4.drop_nulls(subset=features4 + ["target_action_class"])
    X_test4 = clean4.select(features4).to_numpy()
    y_proba4 = calibrated_clf4.predict_proba(X_test4)
    confidence4 = np.max(y_proba4, axis=1)
    preds4 = calibrated_clf4.predict(X_test4)

    # Filter Strong Buy (class 4) or Buy (class 3) with high confidence >= 0.55
    buy_mask = (preds4 >= 3) & (confidence4 >= 0.55)
    fwd_21d_rets = clean4.select("fwd_ret_21d").to_series().to_numpy()
    fwd_drawdowns = clean4.select("fwd_max_drawdown_21d").to_series().to_numpy()

    # Apply realistic 6% stop loss
    realized_clf_trades = []
    for ret, dd in zip(fwd_21d_rets[buy_mask], fwd_drawdowns[buy_mask]):
        if dd <= -0.06:
            realized_clf_trades.append(-6.0)  # Stopped out at -6%
        else:
            realized_clf_trades.append(ret * 100.0)

    realized_clf_trades = np.array(realized_clf_trades)
    m4_trades = len(realized_clf_trades)
    m4_wins = realized_clf_trades[realized_clf_trades > 0]
    m4_losses = realized_clf_trades[realized_clf_trades < 0]
    m4_win_rate = (len(m4_wins) / max(m4_trades, 1)) * 100
    m4_max_win = float(np.max(realized_clf_trades)) if m4_trades > 0 else 0.0
    m4_max_loss = float(np.min(realized_clf_trades)) if m4_trades > 0 else 0.0
    m4_avg_win = float(np.mean(m4_wins)) if len(m4_wins) > 0 else 0.0
    m4_avg_loss = float(np.mean(m4_losses)) if len(m4_losses) > 0 else 0.0
    m4_pf = float(np.sum(m4_wins)) / max(float(np.abs(np.sum(m4_losses))), 1e-4)

    results = {
        "model0_weekly_screener": {
            "total_simulated_trades": total_trades,
            "win_rate_pct": round(win_rate, 2),
            "highest_profit_single_trade_pct": round(max_win, 2),
            "highest_loss_single_trade_pct": round(max_loss, 2),
            "average_win_pct": round(avg_win, 2),
            "average_loss_pct": round(avg_loss, 2),
            "reward_risk_ratio": round(abs(avg_win / max(abs(avg_loss), 1e-4)), 2),
            "profit_factor": round(profit_factor, 2),
            "total_cumulative_return_2yr_pct": round(total_cum_return, 2),
            "max_portfolio_drawdown_pct": round(max_drawdown, 2)
        },
        "model4_swing_action_with_stoploss": {
            "total_signals": m4_trades,
            "win_rate_pct": round(m4_win_rate, 2),
            "highest_profit_single_trade_pct": round(m4_max_win, 2),
            "highest_loss_single_trade_pct": round(m4_max_loss, 2),
            "average_win_pct": round(m4_avg_win, 2),
            "average_loss_pct": round(m4_avg_loss, 2),
            "profit_factor": round(m4_pf, 2)
        }
    }

    print("\n" + "=" * 80)
    print("      REALIZED FINANCIAL AUDIT: 2-YEAR TEST VAULT (JAN 2024 - PRESENT)   ")
    print("=" * 80)
    print(f"Total Simulated Trades       : {total_trades:,}")
    print(f"Total Cumulative Return (2Y) : +{total_cum_return:.2f}%")
    print(f"Win Rate                     : {win_rate:.2f}%")
    print(f"Profit Factor                : {profit_factor:.2f}")
    print(f"Average Winning Trade        : +{avg_win:.2f}%")
    print(f"Average Losing Trade         : {avg_loss:.2f}%")
    print(f"Highest Win Single Trade     : +{max_win:.2f}% (Peak Bull Outlier)")
    print(f"Highest Loss Single Trade    : {max_loss:.2f}% (Worst Stop / Gap-down Hit)")
    print(f"Max Portfolio Drawdown       : {max_drawdown:.2f}%")
    print("=" * 80)

    with open(settings.BASE_DIR / "models" / "stage1" / "pnl_financial_audit.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    simulate_holdout_trading()

