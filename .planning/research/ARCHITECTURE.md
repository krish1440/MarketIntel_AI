# ARCHITECTURE.md — System Design & Data Flow

## High-Level Architecture
The system follows a **Modular Multimodal Pipeline** where data collection, processing, and prediction are decoupled.

## 1. Data Pipeline
- **Price Ingestion**: Periodic polling (every 1-5 mins) of `nsepython` for live quotes.
- **News Ingestion**: Scraping RSS feeds and news sites every 15-30 mins.
- **Preprocessing**: 
  - Price normalization and technical indicator calculation (TA-Lib or Pandas-TA).
  - News tokenization and cleaning for BERT.

## 2. Multimodal Model Design (Late Fusion)
We will use **Late Fusion** because it allows training individual experts (Price vs Text) separately, which is more stable for financial data.

- **Expert A (Temporal)**: LSTM/GRU network. 
  - *Input*: Window of OHLCV data + Technical Indicators.
  - *Output*: Feature vector representing price momentum.
- **Expert B (Semantic)**: DistilBERT.
  - *Input*: Recent news headlines and summaries.
  - *Output*: Sentiment score (-1 to 1).
- **Meta-Learner**: XGBoost.
  - *Input*: Output from Expert A + Sentiment from Expert B + Volume/Volatility signals.
  - *Target*: Probability of price increase/decrease over next N intervals.

## 3. Database Schema (PostgreSQL)
- **`stocks`**: Meta-info (Ticker, ISIN, Industry).
- **`price_history`**: Time-series data (Timestamp, Open, High, Low, Close, Volume).
- **`news_feed`**: (Timestamp, Source, Headline, Summary, Raw_Text).
- **`predictions`**: (StockID, Timestamp, AI_Score, Sentiment_Component, Price_Component).

## 4. UI Architecture (Stitch)
- **State Management**: Local state synchronized with Backend via REST/WebSockets.
- **Modular Components**:
  - `HeaderTicker`
  - `WatchlistSidebar`
  - `MainChartArea`
  - `IntelligencePanel` (Prediction displays)

---
*Last updated: 2026-04-24*
