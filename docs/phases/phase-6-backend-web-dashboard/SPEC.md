# Phase 6: FastAPI Backend & Modern Web Dashboard

## 1. Objectives & Scope
- **FastAPI High-Performance Backend**:
  - Asynchronous REST endpoints for historical candlesticks, stock search, sector performance, and paper trading.
  - Native WebSockets streaming live quote updates and trade execution notifications directly from Redis Pub/Sub.
- **Modern Institutional Web Dashboard (React / Next.js)**:
  - **Market Breadth & Overview**: Nifty 50, Bank Nifty, India VIX cards, Advance/Decline ratio, Sector performance treemap/heatmap.
  - **Stock Terminal & Search**: Instant debounce search across NSE & BSE; interactive TradingView Lightweight Charts with timeframe toggles (1m, 5m, 1h, 1D) and technical overlays.
  - **AI Insights Panel**:
    - Directional Gauge (Buy / Hold / Sell) with calibrated percentage confidence.
    - SHAP Driver breakdown (top bullish and bearish reasons).
    - Actionable trade setup: Recommended Entry, Dynamic SL, Target 1, Target 2.
    - Probabilistic Price Corridor chart (P10, P50, P90).
  - **Active Paper Trading Terminal**:
    - Live virtual portfolio equity curve.
    - Open positions table with live unrealized PnL.
    - Historical trade journal with filterable execution logs and metrics (Win Rate, Sharpe Ratio, Max Drawdown).

## 2. API Endpoints Specification

### REST Endpoints:
- `GET /api/v1/securities/search?q={query}`: Instant stock search across NSE & BSE.
- `GET /api/v1/securities/{symbol}/overview`: Complete company profile, sector, and key statistics.
- `GET /api/v1/market/sectors`: Real-time sector relative performance and heatmap data.
- `GET /api/v1/market/screener/focus-list`: Today's Top 20 Focus Stocks (Top 10 Longs & Shorts).
- `GET /api/v1/charts/{symbol}/candles?timeframe=1m&limit=500`: High-speed historical candles.
- `GET /api/v1/ai/insights/{symbol}`: Probabilistic Buy/Hold/Sell signal, SHAP drivers, and dynamic levels.
- `GET /api/v1/paper-trading/portfolio`: Virtual portfolio equity, cash balance, and open positions.
- `GET /api/v1/paper-trading/trades`: Filterable trade journal and performance statistics.

### WebSocket Endpoints:
- `WS /ws/live-quotes`: Real-time streaming prices, LTP updates, and market depth for subscribed tickers.
- `WS /ws/trade-notifications`: Real-time paper order fill, partial profit exit, and stop-loss notifications.

## 3. Implementation Steps & Milestones
- [ ] Step 6.1: Initialize FastAPI project structure with CORS, dependencies, and Redis pub/sub listener.
- [ ] Step 6.2: Implement REST API endpoints for securities, charts, screener, and AI insights.
- [ ] Step 6.3: Implement WebSocket server for low-latency live tick streaming.
- [ ] Step 6.4: Set up Next.js frontend with Tailwind CSS and TradingView Lightweight Charts.
- [ ] Step 6.5: Build Market Overview, Sector Heatmap, and Top Screener widgets.
- [ ] Step 6.6: Build AI Insights panel (Gauge, SHAP explanations, Price Corridor).
- [ ] Step 6.7: Build Paper Trading monitor and interactive performance dashboard.

