# Requirements: Multimodal Stock Market Intelligence System

**Defined:** 2026-04-24
**Core Value:** Empower retail investors with institutional-grade multimodal predictive insights by fusing quantitative price action with qualitative market sentiment.

## v1 Requirements

### Data Acquisition (DATA)
- [ ] **DATA-01**: Fetch live stock prices from NSE and BSE via `nsepython` and `bsedata`.
- [ ] **DATA-02**: Fetch historical OHLCV data for specified symbols via `yfinance`.
- [ ] **DATA-03**: Aggregate news headlines and summaries from financial news RSS feeds and Google News.
- [ ] **DATA-04**: Store all fetched data in a local PostgreSQL database with appropriate indexing.

### Intelligence Models (INTL)
- [ ] **INTL-01**: Train an LSTM model to extract temporal features from historical price data.
- [ ] **INTL-02**: Implement a DistilBERT-based sentiment analyzer for processed news text.
- [ ] **INTL-03**: Train an XGBoost meta-learner to fuse LSTM features, sentiment scores, and technical indicators.
- [ ] **INTL-04**: Optimize models for Intel Iris Xe GPU using `intel_extension_for_pytorch` (IPEX).

### Market Dashboard (DASH)
- [ ] **DASH-01**: Real-time ticker for major indices (NIFTY 50, SENSEX).
- [ ] **DASH-02**: Interactive watchlist with live price updates and sparklines.
- [ ] **DASH-03**: Visual "AI Confidence" gauge and "Sentiment Score" display for selected stocks.
- [ ] **DASH-04**: Integrated news feed with sentiment color-coding.
- [ ] **DASH-05**: Detailed stock view with interactive candlestick charts and technical overlays.

### System & Infrastructure (SYS)
- [ ] **SYS-01**: Implement periodic automated retraining (daily/weekly) to handle "over-time learning."
- [ ] **SYS-02**: Provide a high-performance local database setup on Windows.
- [ ] **SYS-03**: Ensure responsive UI performance using the Stitch design system.

## v2 Requirements (Deferred)
- **AUTH-01**: User accounts and cloud synchronization.
- **BOT-01**: Automated paper trading based on AI signals.
- **ALRT-01**: Push notifications for predicted significant price movements.
- **HFT-01**: Sub-minute tick-by-tick analysis (v1 is 1-min to 1-day).

## Out of Scope
| Feature | Reason |
|---------|--------|
| Direct Brokerage Integration | High complexity and security risk for v1. |
| Mobile Application | Web-first focus; mobile can be wrapped later. |
| Global Markets (US/EU) | Focused on BSE/NSE as requested. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| SYS-02 | Phase 1 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| INTL-01 | Phase 3 | Pending |
| INTL-02 | Phase 3 | Pending |
| INTL-04 | Phase 3 | Pending |
| INTL-03 | Phase 4 | Pending |
| SYS-01 | Phase 4 | Pending |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |
| SYS-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after initial definition*
