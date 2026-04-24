# Roadmap: Multimodal Stock Market Intelligence System

## Overview
This roadmap outlines the journey from a raw data pipeline to a professional-grade multimodal intelligence dashboard. We start with the foundation of data and infrastructure, build individual expertise in price and sentiment models, fuse them into a meta-learner, and finally wrap everything in a premium Stitch-powered UI.

## Phases

- [ ] **Phase 1: Foundation & Data Ingestion** - Establish the local database and live BSE/NSE data scrapers.
- [ ] **Phase 2: Historical & News Pipeline** - Implement historical data fetching and real-time news aggregation.
- [ ] **Phase 3: Model Experts (Price & Text)** - Train the individual LSTM and DistilBERT models with Intel IPEX optimization.
- [ ] **Phase 4: Multimodal Fusion & Intelligence** - Develop the XGBoost meta-learner and automated retraining logic.
- [ ] **Phase 5: Premium Market Dashboard** - Build the Moneycontrol-like UI using Stitch and connect to the intelligence backend.

## Phase Details

### Phase 1: Foundation & Data Ingestion
**Goal**: A working local PostgreSQL database and live NSE/BSE price polling system.
**Depends on**: Nothing
**Requirements**: DATA-01, DATA-04, SYS-02
**Success Criteria**:
  1. PostgreSQL database is accessible on Windows.
  2. `nsepython` can fetch live quotes for a list of 10 stocks.
  3. Live quotes are successfully saved to the database.
**Plans**: 2 plans

Plans:
- [ ] 01-01: Local PostgreSQL setup and schema initialization.
- [ ] 01-02: Live polling service implementation using `nsepython` and `bsedata`.

### Phase 2: Historical & News Pipeline
**Goal**: Full coverage of historical data and a live news aggregator.
**Depends on**: Phase 1
**Requirements**: DATA-02, DATA-03
**Success Criteria**:
  1. `yfinance` can backfill 1 year of daily OHLCV data for 50 stocks.
  2. News aggregator fetches headlines from Google News RSS.
  3. Sentiment news table is populated in the database.
**Plans**: 2 plans

Plans:
- [ ] 02-01: Historical data backfilling service.
- [ ] 02-02: News scraper and RSS aggregator.

### Phase 3: Model Experts (Price & Text)
**Goal**: Optimized LSTM and DistilBERT models running on Intel Iris Xe.
**Depends on**: Phase 2
**Requirements**: INTL-01, INTL-02, INTL-04
**Success Criteria**:
  1. LSTM model produces feature vectors from price history.
  2. DistilBERT produces sentiment scores for news headlines.
  3. Models utilize the Intel `xpu` device via IPEX for acceleration.
**Plans**: 3 plans

Plans:
- [ ] 03-01: LSTM temporal feature extractor development.
- [ ] 03-02: DistilBERT sentiment analyzer integration.
- [ ] 03-03: IPEX optimization and hardware profiling.

### Phase 4: Multimodal Fusion & Intelligence
**Goal**: A unified predictive engine with automated retraining.
**Depends on**: Phase 3
**Requirements**: INTL-03, SYS-01
**Success Criteria**:
  1. XGBoost model combines signals to produce a single bullish/bearish probability.
  2. Automated script performs model retraining on new weekly data.
  3. Backtest results show predictive accuracy better than random chance.
**Plans**: 2 plans

Plans:
- [ ] 04-01: XGBoost meta-learner and fusion logic.
- [ ] 04-02: Incremental learning and retraining automation.

### Phase 5: Premium Market Dashboard
**Goal**: A stunning, Moneycontrol-like web UI powered by Stitch.
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, SYS-03
**Success Criteria**:
  1. Dashboard displays live NIFTY/SENSEX indices.
  2. Watchlist shows sparklines and AI prediction scores.
  3. Detailed view features interactive charts and sentiment feeds.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Stitch project creation and layout design.
- [ ] 05-02: Real-time data binding and charting integration.
- [ ] 05-03: Intelligence panel and final polish.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Not started | - |
| 2. Historical & News | 0/2 | Not started | - |
| 3. Model Experts | 0/3 | Not started | - |
| 4. Fusion | 0/2 | Not started | - |
| 5. Dashboard | 0/3 | Not started | - |

---
*Roadmap defined: 2026-04-24*
*Last updated: 2026-04-24 after initial planning*
