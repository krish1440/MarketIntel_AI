# 🚀 TradeIntellect: Total Market Intelligence Engine

TradeIntellect is a production-grade, high-performance market monitoring and prediction platform. It provides **total market coverage** for over 2,300+ stocks across the NSE (National Stock Exchange) and BSE (Bombay Stock Exchange), powered by real-time data, batch history ingestion, and AI-driven news sentiment.

---

## 💎 Core Capabilities

### 🏛️ Total Market Coverage
*   **2,361+ Symbols**: Fully mapped and seeded equity list covering both NSE and BSE.
*   **Dual-Exchange Monitoring**: Switch between NSE and BSE benchmarks with a single click.
*   **Smart Discovery**: Automated symbol discovery engine that identifies new listings and updates.

### ⚡ High-Performance Data Pipeline
*   **Fast Batch Ingestion**: Uses a high-speed 50-stock batch fetching method (5-year history backfill).
*   **Idempotent & Robust**: Resumable downloads with built-in duplicate protection and rate-limit awareness.
*   **Real-Time Poller**: Multi-threaded 100-stock chunk polling ensures the entire market is tracked every minute.

### 🧠 AI-Driven News Intelligence
*   **Rotational News Engine**: Background service that cycles through all 2,300+ stocks safely to avoid IP bans.
*   **Broad Market Mapping**: Automatically tags global business headlines to specific tickers using keyword intelligence.
*   **Instant Fetch**: Real-time news refresh triggered instantly when you open a stock detail page.
*   **Sentiment Analysis**: (Placeholder) Ready for LSTM/Transformer-based sentiment scoring.

### 📈 Predictive Analytics
*   **LSTM Neural Network**: Trained on 1.6M+ historical data points for multi-day price forecasting.
*   **Technical Suite**: Integrated RSI, MACD, SMA, ATR, and Bollinger Band calculations.
*   **Fusion Signal**: Combines technical indicators with AI forecasts into a single **BUY/SELL** signal.

---

## 🛠️ Technology Stack

*   **Frontend**: Next.js 14, Tailwind CSS, Lucide Icons.
*   **Backend**: FastAPI, SQLAlchemy (PostgreSQL).
*   **Database**: PostgreSQL (Dockerized) with 1.6M+ historical records.
*   **Ingestion**: Python, FeedParser, BeautifulSoup4, yFinance.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10+
*   Docker & Docker Compose
*   Node.js & npm

### 2. One-Command Setup
TradeIntellect uses a **Master Orchestrator** to handle everything. You do not need to run individual scripts.

```powershell
python run_app.py
```

### 3. What happens next?
*   **Docker DB**: Starts automatically.
*   **Market Discovery**: Seeds all 2,300+ stocks if the DB is empty.
*   **Batch Backfill**: Downloads 5 years of data for all stocks (idempotent).
*   **Live Services**: Launches the API, Poller, News Engine, and Dashboard in separate windows.

---

## 📊 Dashboard Access
*   **Terminal UI**: `http://localhost:3000`
*   **Interactive API**: `http://localhost:8000/docs`

---

## 📜 Maintenance
The platform is designed to be **Zero-Touch**. 
*   **Daily Sync**: Every time you run `run_app.py`, it automatically fills gaps for missing dates (e.g., after weekends).
*   **News Rotation**: The background news service manages its own schedule to ensure 24/7 market coverage.

---
*Built with precision for the modern trader.*
