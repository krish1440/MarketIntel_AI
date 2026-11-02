# Frontend Functional Specification & Requirements

This document defines the functional capabilities, tabs, controls, data inputs, and interactions for the MarketIntel frontend. It describes pure functionality, data flows, and backend API integration without specifying colors, themes, styling, or visual design aesthetics.

---

## 1. Top Navigation & Global Header

### Functional Capabilities:
1. **Universal Stock Search Input**:
   - **User Action**: Type any stock symbol or company name prefix (e.g. `REL`, `TATA`, `HDFC`).
   - **Behavior**: Sub-10 millisecond auto-complete list querying `/api/stocks/search?q={query}` across all 2,357 NSE/BSE equities.
   - **Display Data**: Symbol, Company Name, Exchange (`NSE`), Token, Top 300 Universe badge indicator.
   - **Selection**: Clicking any search result updates the active stock symbol across the chart, quotes, AI forecaster, and order panel.

2. **Active Stock Ticker Bar**:
   - **Backend Source**: `GET /api/stocks/quote/{symbol}` + live tick updates via WebSocket `/ws/live`.
   - **Data Fields Displayed**:
     - Symbol & Company Name.
     - Last Traded Price (LTP).
     - Absolute Net Change in ₹ (Current Price - Previous Close).
     - Percentage Net Change (`%`).
     - Day Open, Day High, Day Low.
     - Cumulative Day Volume.
     - Volume-Weighted Average Price (VWAP).
     - 52-Week High & 52-Week Low.

3. **System Telemetry & Market Clock**:
   - **Backend Source**: `GET /api/system/health`.
   - **Data Fields**:
     - Current IST Time (Indian Standard Time clock).
     - Market Session State: `PRE_MARKET` (09:00–09:15), `LIVE_MARKET` (09:15–15:30), `POST_MARKET` (15:30–16:30), or `WEEKEND_CLOSED`.
     - Data Feed Status: WebSocket connected / disconnected indicator with automatic reconnection logic.
     - Lakehouse & Memory Footprint metrics (Silver stocks count, Memory RSS in MB).

4. **Market Breadth Indicator**:
   - **Backend Source**: `GET /api/stocks/breadth`.
   - **Data Fields**: Total Advances count, Total Declines count, Unchanged count, and Advance/Decline Ratio across active equities.

---

## 2. Interactive Candlestick Charting Module

### Functional Capabilities:
1. **Timeframe Selector**:
   - **Options**: `1m` (1 Minute), `5m` (5 Minute), `15m` (15 Minute), `1h` (1 Hour), `1d` (1 Daily).
   - **Backend Source**: `GET /api/charts/{symbol}?timeframe={tf}&limit=500&auto_backfill=true`.
   - **Data Structure**: Array of candles containing UNIX timestamp (seconds), Open, High, Low, Close, Volume, and VWAP.

2. **Charting Canvas**:
   - **Main Price Panel**:
     - Candlestick series plotting Open, High, Low, Close.
     - Optional VWAP overlay line for intraday timeframes (`1m`, `5m`, `15m`).
     - Horizontal overlay levels showing Model 3 AI Price Corridor:
       - $P_{05}$ Level: Floor / Stop-Loss.
       - $P_{50}$ Level: Expected Median Price.
       - $P_{75}$ Level: Target 1 Profit Booking.
       - $Q_{90}$ Level: Upper Runner Target.
   - **Sub-Panel (Volume Histogram)**:
     - Vertical bars representing trading volume per candle bar.
   - **On-Demand Lazy Catchup**:
     - If viewing an intraday stock that has offline gaps, the backend automatically backfills missing bars via SmartAPI in $<300\text{ms}$ without requiring page refresh.
   - **Real-Time Candle Updating**:
     - Subscribed to `/ws/live`. When new ticks arrive for the active stock, the latest open bar updates its High, Low, Close, and Volume in real-time. When a new minute elapses, a new candle bar appends automatically.

---

## 3. AI Quantitative Intelligence Panel

### Tab A: Pre-Market Focus Screener (Model 0)
- **Backend Source**: `GET /api/ai/screener/focus?limit=20`.
- **Purpose**: Displays the top 20 institutional focus candidates selected daily at 09:08 AM.
- **Table Columns**:
  1. Rank (1 to 20).
  2. Symbol.
  3. Company Name.
  4. Sector / Industry.
  5. 20-Day Rolling Turnover (₹ Crores).
  6. Opening Gap % / Intraday Momentum score.
  7. Conviction Score (0.0 to 1.0).
- **Interaction**: Clicking any row loads that stock immediately into the chart and analysis panels.

### Tab B: Probabilistic Price Corridor Forecast (Model 3)
- **Backend Source**: `GET /api/ai/forecast/corridor/{symbol}`.
- **Purpose**: Quantile Regression multi-target price corridor prediction for current session.
- **Data Points Displayed**:
  - Current Spot Price.
  - $P_{05}$ (Downside Risk Floor / Stop level).
  - $P_{25}$ (Lower quartile expected range).
  - $P_{50}$ (Median expected price outcome).
  - $P_{75}$ (Upper quartile / Target 1 booking level).
  - $Q_{90}$ (Upper volatility breakout / Target 2 runner level).
  - Projected Volatility Band width (in ₹ and %).

### Tab C: Calibrated Strategy Signal & Risk Evaluation (Model 4 & Execution Rules)
- **Backend Source**: `GET /api/ai/signal/{symbol}`.
- **Purpose**: Calibrated directional signal with concrete execution boundaries.
- **Data Fields Displayed**:
  - Recommended Action: `STRONG_BUY`, `BUY`, `HOLD`, or `AVOID`.
  - Platt-Calibrated Probability Score (e.g. 74.2% conviction).
  - Regime Classification: `TRENDING_LOW_VOLATILITY`, `MEAN_REVERTING`, or `HIGH_VOLATILITY_BREAKOUT`.
  - Recommended Stop-Loss Price.
  - Recommended Target 1 (35% partial exit) and Target 2 (runner exit).
  - Risk-to-Reward Ratio (e.g. 1 : 2.6).

---

## 4. Simulated Paper Trading & Execution Module

### Tab A: Portfolio Overview & Governance Scorecard
- **Backend Source**: `GET /api/trading/portfolio`.
- **Data Fields Displayed**:
  - Initial Capital: Fixed ₹10,00,000.00 INR baseline.
  - Available Cash Balance (₹).
  - Total Invested Capital (₹ in open positions).
  - Total Portfolio Value = Cash + Current Market Value of Open Positions.
  - Total Return % = `((Total Value - Initial Capital) / Initial Capital) * 100`.
  - Total Realized P&L (₹ from completed trades).
  - Total Unrealized P&L (₹ from live open positions).
  - Daily P&L % (vs today's day start baseline).
  - Peak Drawdown % (vs all-time high portfolio value).
  - Circuit Breaker Status: `NORMAL` (Active) or `TRIPPED` (Halted if daily loss exceeds -3.0%).

### Tab B: Active Positions Table
- **Backend Source**: `GET /api/trading/positions` + WebSocket `/ws/trades`.
- **Purpose**: Real-time monitoring of all open paper trades.
- **Table Columns**:
  1. Symbol.
  2. Entry Timestamp.
  3. Entry Price (₹).
  4. Live Current Price (₹).
  5. Quantity (Shares).
  6. Invested / Allocated Capital (₹).
  7. Unrealized P&L (₹).
  8. Unrealized P&L (%).
  9. Stop-Loss Price Level (₹) — dynamically moves to Breakeven after Target 1.
  10. Target 1 Price Level (₹).
  11. Target 2 Price Level (₹).
  12. Partial Exit Status: `Pending` or `Booked (35%)`.
  13. Action Button: **"Square Off"** — triggers `POST /api/trading/close/{symbol}` to exit position immediately at live market price.

### Tab C: Manual Simulated Order Placement Form
- **Backend Source**: `POST /api/trading/order`.
- **Form Controls & Inputs**:
  - **Symbol**: Auto-filled from active chart or selectable via search dropdown.
  - **Order Direction**: Toggle buttons for `BUY` or `SELL`.
  - **Order Type**: `MARKET` (executes at current live tick price) or `LIMIT` (requires Price input).
  - **Quantity Input**: Number of shares (or leave blank for institutional risk-based auto-sizing).
  - **Limit Price Input**: Enabled only when LIMIT is selected.
  - **Action Button**: **"Submit Simulated Order"**.
- **Governance Behavior**:
  - If daily circuit breaker is tripped, form is disabled with warning.
  - If 10 concurrent positions are already open, order is rejected with limit message.
  - Successful order triggers a confirmation toast and updates the Active Positions table instantly.

### Tab D: Closed Trade History & Indian Tax Audit Log
- **Backend Source**: `GET /api/trading/trades?limit=50`.
- **Purpose**: Full institutional accounting ledger of all realized trades with statutory friction breakdowns.
- **Table Columns**:
  1. Trade ID.
  2. Symbol.
  3. Entry Time & Exit Time.
  4. Holding Period (Days).
  5. Quantity Executed.
  6. Entry Price & Exit Price.
  7. Gross P&L (₹ and %).
  8. Statutory Transaction Frictions (STT, Exchange Turnover charges, SEBI fees, Stamp Duty, GST).
  9. Capital Gains Tax Deducted (₹) and Tax Type (`STCG 20%` or `LTCG 12.5%`).
  10. Net Realized P&L (₹ and %).
  11. Exit Trigger (`P05_STOP_LOSS`, `P75_TARGET_1_PARTIAL`, `Q90_RUNNER_TARGET`, `BREAKEVEN_STOP`, or `MANUAL_EXIT`).

---

## 5. Top 300 Institutional Universe Screener

### Functional Capabilities:
- **Backend Source**: `GET /api/stocks/universe/top300?limit=300`.
- **Filter & Sort Controls**:
  - Search filter by symbol or company name.
  - Sort by: 20-Day Average Turnover (₹ Cr), Current Price, Day Change %, or Symbol.
- **Table Columns**:
  1. Symbol.
  2. Company Name.
  3. Last Price (₹).
  4. Change % (24h).
  5. 20-Day Rolling Turnover (₹ Crores).
  6. Liquidity Rank (1 to 300).
- **Interaction**: Single click selects the stock and updates the entire dashboard.

---

## 6. System Operations & Data Management Modal

### Functional Capabilities:
1. **Engine Health Dashboard**:
   - Memory RSS usage tracker.
   - DuckDB Lakehouse table counts (Silver 1D files, Silver 1M partitions).
   - Redis Broker status: `CONNECTED_LIVE` or `IN_MEMORY_FALLBACK`.
   - Engine Execution Mode: `PAPER`.
2. **Lakehouse Synchronization Actions**:
   - **Button: "Sync Daily 1D & Re-Compute Features"**:
     - Calls `POST /api/system/sync?mode=daily`. Runs full universe 1D gap syncer and updates Gold ML features.
   - **Button: "Sync Intraday 1M Universe"**:
     - Calls `POST /api/system/sync?mode=hybrid`. Runs intraday 1-minute backfill for active leaders.
   - **Button: "Re-Rank Top 300 Turnover Leaders"**:
     - Calls `POST /api/system/sync?mode=refresh_ranking`. Dynamically evaluates rolling 20-day volume $\ge ₹2\text{ Cr}$ and price $\ge ₹30$.
   - **Sync Progress / Status Indicator**:
     - Polls `GET /api/system/sync/status` to show whether background sync is currently running or idle.

---

## 7. Real-Time Notification & Alerting Feed

### Functional Capabilities:
- Connected to WebSocket channel `/ws/trades`.
- **Event Types Triggering Notifications**:
  - **Order Fill Event**: Notification when a simulated trade executes (Symbol, Shares, Fill Price).
  - **Target 1 Hit Event**: Notification when a position reaches $P_{75}$ target, books 35% profit, and moves stop-loss to breakeven.
  - **Stop-Loss Hit Event**: Warning notification when a position is stopped out.
  - **Runner Target Hit Event**: Profit booking notification when Model 1 $Q_{90}$ is reached.
  - **Circuit Breaker Halt Alert**: Critical notification if the portfolio hits -3% daily drawdown and halts new entries.
