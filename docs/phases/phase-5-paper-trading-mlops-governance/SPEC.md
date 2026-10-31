# Phase 5: Autonomous Paper Trading & MLOps Champion/Challenger Governance

## 1. Objectives & Scope
- **Autonomous Paper Trading Simulator**:
  - Virtual order matching engine with realistic execution mechanics:
    - Estimated slippage model (0.05% on market orders).
    - Indian statutory transaction costs: STT (Securities Transaction Tax), Exchange Transaction Charges, SEBI turnover fees, Stamp Duty, and GST.
  - Active position manager with automated stop-loss tracking and partial profit exits (+1.5R).
- **Real-Time Trade Ledger & Performance Analytics**:
  - Maintains persistent order book, trade journal, and equity curve.
  - Key institutional metrics:
    - **Sharpe Ratio** & **Sortino Ratio**
    - **Maximum Drawdown (MDD)**
    - **Win Rate (%)** and **Profit Factor ($\frac{\text{Gross Profit}}{\text{Gross Loss}}$)**
- **Champion vs. Challenger MLOps Governance**:
  - Scheduled weekly execution: **Every Saturday at 02:00 AM IST**.
  - **Delta-Only Ingestion**: Only the new 5 days of Gold features are processed; historical partitions remain frozen.
  - **Warm Retraining**: LightGBM `init_model` starts from the existing Champion weights, learning new residual trees in seconds.
  - **Validation Gate**: Both models backtested on out-of-sample data. Challenger is promoted to Champion only if it beats the baseline on Sharpe ratio, win rate, and drawdown.

## 2. Technical Contracts & Schemas

### Trade Journal Schema:
```sql
CREATE TABLE paper_trades (
    trade_id UUID PRIMARY KEY,
    symbol VARCHAR(30) NOT NULL,
    direction VARCHAR(5) NOT NULL, -- BUY or SELL
    entry_time TIMESTAMPTZ NOT NULL,
    entry_price REAL NOT NULL,
    initial_sl REAL NOT NULL,
    target_1 REAL NOT NULL,
    target_2 REAL,
    quantity INT NOT NULL,
    allocated_capital REAL NOT NULL,
    exit_time_part1 TIMESTAMPTZ,
    exit_price_part1 REAL,
    exit_time_part2 TIMESTAMPTZ,
    exit_price_part2 REAL,
    slippage_cost REAL DEFAULT 0,
    statutory_taxes REAL DEFAULT 0,
    net_pnl REAL,
    net_pnl_pct REAL,
    exit_reason VARCHAR(50), -- TARGET_1_HIT, TRAILING_SL_HIT, STOP_LOSS_HIT
    status VARCHAR(20) DEFAULT 'OPEN' -- OPEN, PARTIAL_CLOSED, CLOSED
);
```

### MLOps Evaluation Report Schema:
```json
{
  "evaluation_date": "2024-11-02T02:30:00+05:30",
  "champion_id": "model_v2.1",
  "challenger_id": "model_v2.2_candidate",
  "test_window": "2024-10-28 to 2024-11-01",
  "metrics": {
    "champion": {"sharpe": 1.84, "win_rate": 0.61, "max_drawdown": 0.042, "profit_factor": 1.95},
    "challenger": {"sharpe": 2.10, "win_rate": 0.64, "max_drawdown": 0.038, "profit_factor": 2.21}
  },
  "gate_decision": "PROMOTE",
  "promoted_to_champion": true,
  "reason": "Challenger achieved superior Sharpe (+0.26) and lower Drawdown (-0.4%) with positive expectancy."
}
```

## 3. Implementation Steps & Milestones
- [ ] Step 5.1: Build Virtual Order Execution Engine with slippage and tax calculations.
- [ ] Step 5.2: Implement Trade Journal database table and portfolio equity tracker.
- [ ] Step 5.3: Build performance analytics calculator (Sharpe, Sortino, Drawdown, Profit Factor).
- [ ] Step 5.4: Implement delta feature fetcher and LightGBM warm-start incremental retrainer.
- [ ] Step 5.5: Implement automated Champion vs Challenger backtest validation gate.

