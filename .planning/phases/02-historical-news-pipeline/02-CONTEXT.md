# Phase 2: Historical & News Pipeline - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase focuses on populating the database with historical price data for longitudinal analysis and setting up a news ingestion engine. This data is essential for training the LSTM (Phase 3) and the multimodal fusion model (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Historical Data
- **Library**: `yfinance`.
- **Symbols**: Map local tickers to Yahoo Finance tickers (e.g., `RELIANCE` -> `RELIANCE.NS`).
- **Interval**: Daily OHLCV for the last 1-2 years to start.

### News Aggregation
- **Sources**: Google News RSS (Financial section), Moneycontrol RSS feeds.
- **Library**: `feedparser` for RSS and `BeautifulSoup` for detail scraping if necessary.
- **Storage**: Store headline, summary, link, and timestamp. Sentiment score field will be initialized to NULL (to be filled in Phase 3).

### Database Updates
- Ensure `live_quotes` can also hold historical daily records or create a dedicated `historical_prices` table for cleaner separation.
- Decision: Create `historical_prices` for EOD data to avoid bloating the `live_quotes` table which is for real-time monitoring.

</decisions>

<canonical_refs>
## Canonical References
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md` (DATA-02, DATA-03)
- `.planning/research/ARCHITECTURE.md`

</canonical_refs>

<specifics>
## Specific Ideas
- Implement a `backfill_history.py` script.
- Implement a `news_aggregator.py` service that runs periodically.

</specifics>

---
*Phase: 02-historical-news-pipeline*
*Context gathered: 2026-04-25*
