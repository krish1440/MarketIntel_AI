# 🛰️ Ingestion Layer: MarketIntel AI

The Ingestion Layer is the "heartbeat" of MarketIntel AI. It manages the multi-threaded acquisition of financial data from various sources, ensuring the system has high-density historical data, real-time price updates, and sentiment-aware news.

---

## 🏗️ Architecture Overview

The ingestion engine is comprised of six specialized services designed for reliability, rate-limit compliance, and data integrity.

### 1. 📂 Data Orchestrators
- **`backfill_history.py`**: The heavy-duty engine for initial setup. It fetches 5 years of historical OHLCV (Open, High, Low, Close, Volume) data for all registered stocks.
- **`delta_update.py`**: The "Smart Sync" engine. It runs daily to identify and patch "data holes" (e.g., weekend gaps or missed trading days) without redundant fetching.

### 2. ⚡ Real-Time Pipeline
- **`poll_prices.py`**: A high-frequency poller that retrieves 1-minute interval price data. It updates the `live_quotes` table to drive the dashboard.

### 3. 📰 Intelligence & News
- **`news_aggregator.py`**: A rotational scraper that monitors Google News RSS feeds. It performs dual-fetch (broad market vs specific ticker) and triggers the AI Sentiment model (DistilBERT) in real-time.
- **`update_sentiment.py`**: A background utility that performs retroactive sentiment analysis on any articles that missed the real-time trigger.

### 4. 🗺️ Symbol Discovery
- **`discover_symbols.py`**: The system's "Mapmaker". It uses `nsepython` and `bsedata` to discover every tradable equity on the NSE and BSE, mapping them to Yahoo Finance tickers.

---

## 🛠️ Technical Implementation

### 🔄 Idempotency & Data Integrity
- **Unique Constraints**: All ingestion services rely on database-level constraints (e.g., `UNIQUE(stock_id, exchange, date)` in `historical_prices`) to prevent duplicate records.
- **Upsert Logic**: Services use `ON CONFLICT` or manual checks to perform "Patch" operations rather than "Overwrites".

### 🏎️ Rate-Limit Protection
To avoid provider bans (especially from Yahoo Finance), the engines implement:
- **Batch Chunking**: Tickers are processed in groups of 20-50.
- **Cooling Periods**: `time.sleep()` is dynamically adjusted based on chunk success/failure.
- **Randomized Jitter**: The news aggregator uses randomized delays to mimic human browsing behavior.

---

## 🚀 Execution Workflow

### Initial Deployment
1. `python discover_symbols.py` (Map the market)
2. `python backfill_history.py` (Fetch 5-year history)

### Production Maintenance (Automatic)
The `run_app.py` script orchestrates the following in the background:
- **Daily**: `delta_update.py` (Patch yesterday's close)
- **Continuous**: `poll_prices.py` (Live dashboard)
- **Continuous**: `news_aggregator.py` (Market mood monitoring)

---

## 🧪 Dependencies
- **yfinance**: Primary OHLCV and Quote provider.
- **nsepython / bsedata**: Symbol discovery engines.
- **feedparser / BeautifulSoup**: RSS and HTML parsing for news.
- **DistilBERT (Local)**: Integrated sentiment analysis junction.
