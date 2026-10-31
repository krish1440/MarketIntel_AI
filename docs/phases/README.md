# MarketIntel: Phase Documentation & Independent Planning Index

Each phase has its own dedicated directory where specifications, data contracts, architectural grilling notes, and checklists are maintained independently.

---

### Directory Map

| Phase | Directory | Focus & Deliverable | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | [`phase-1-master-universe-data-pipeline/`](file:///d:/PROJECT/MarketIntel/docs/phases/phase-1-master-universe-data-pipeline/SPEC.md) | Dual-exchange master universe (NSE & BSE via ISIN), Bhavcopy archive crawler, `yfinance` daily backfill, Broker API 1m candles. | Ready for Planning / Execution |
| **Phase 2** | [`phase-2-medallion-lakehouse-indicators/`](file:///d:/PROJECT/MarketIntel/docs/phases/phase-2-medallion-lakehouse-indicators/SPEC.md) | Local Bronze $\rightarrow$ Silver $\rightarrow$ Gold Lakehouse, Polars-vectorized technical indicators, Candlestick anatomy vectors, DuckDB partition pruning. | Planned |
| **Phase 3** | [`phase-3-realtime-bus-serving-db/`](file:///d:/PROJECT/MarketIntel/docs/phases/phase-3-realtime-bus-serving-db/SPEC.md) | Redis Hashes, Streams & Pub/Sub, TimescaleDB/ClickHouse hypertables, Real-time tick-to-candle streaming aggregator. | Planned |
| **Phase 4** | [`phase-4-ai-engine-adaptive-risk/`](file:///d:/PROJECT/MarketIntel/docs/phases/phase-4-ai-engine-adaptive-risk/SPEC.md) | Pre-market screener (Focus 20), LightGBM/XGBoost Buy/Hold/Sell classifier, SHAP explainability, Dynamic ATR trailing SL, 1% risk position sizing, Monte Carlo price corridor. | Planned |
| **Phase 5** | [`phase-5-paper-trading-mlops-governance/`](file:///d:/PROJECT/MarketIntel/docs/phases/phase-5-paper-trading-mlops-governance/SPEC.md) | Order simulator with slippage & Indian taxes, Trade ledger, Sharpe/Drawdown analytics, Saturday 02:00 AM warm retrainer, Champion-vs-Challenger validation gate. | Planned |
| **Phase 6** | [`phase-6-backend-web-dashboard/`](file:///d:/PROJECT/MarketIntel/docs/phases/phase-6-backend-web-dashboard/SPEC.md) | FastAPI REST & WebSockets, React/Next.js dashboard, TradingView charts, Sector Heatmap, AI Insights panel, Paper trading terminal. | Planned |

---

### How to Use These Folders:
1. **Independent Grilling & Discussions**: We can open any phase directory, discuss its specific nuances, and capture decisions in that phase's documentation.
2. **Modular Implementation**: Work on one phase without tangling code or dependencies with other phases.
3. **Traceability**: Track verification and progress against each phase's specific checklist.

