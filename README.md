# 🚀 MarketIntel AI: Total Market Intelligence Engine
**🏆 Kaggle Bronze Medal Dataset Inside**

MarketIntel AI is a production-grade, high-performance market monitoring and prediction platform. It provides **total market coverage** for over 2,300+ stocks across the NSE (National Stock Exchange) and BSE (Bombay Stock Exchange), powered by real-time data, additive history ingestion, and **AI-driven neural sentiment**.

---

## 📖 Advanced Documentation
For a deep-dive into the neural orchestration and system blueprints, visit our:
👉 **[Full Architecture Handbook & API Catalog (api/ARCHITECT_HANDBOOK.md)](api/ARCHITECT_HANDBOOK.md)**

---

## 💎 Core Capabilities

### 🏛️ Total Market Coverage
*   **2,361+ Symbols**: Fully mapped and seeded equity list covering both NSE and BSE.
*   **Dual-Exchange Monitoring**: Switch between NSE and BSE benchmarks with a single click.
*   **Smart Discovery**: Automated symbol discovery engine that identifies new listings and updates.

### ⚡ Smart-Sync Data Pipeline
*   **Delta Update Engine (New!)**: High-speed incremental fetching that only "patches" missing trading days (idempotent).
*   **Fast Batch Ingestion**: Uses a high-speed 50-stock batch fetching method (5-year history backfill).
*   **Real-Time Poller**: Multi-threaded 100-stock chunk polling ensures the entire market is tracked every minute.

### 🧠 AI-Driven Intelligence
*   **Transformers Sentiment**: Real-time news analysis using **DistilBERT** to generate market mood scores (-1.0 to 1.0) for every headline.
*   **LSTM Neural Network**: Trained on 4.5M+ historical data points for multi-day price forecasting.
*   **Fusion Signal**: Combines technical indicators (RSI, MACD, etc.) with AI forecasts into a single **BUY/SELL** signal.

---

## 🛠️ Technology Stack
*   **Frontend**: Next.js 14, Tailwind CSS, Lucide Icons.
*   **Backend**: FastAPI, SQLAlchemy (PostgreSQL).
*   **Intelligence**: PyTorch (CPU-Optimized), Transformers (Hugging Face).
*   **Database**: PostgreSQL (Dockerized) with 4.5M+ historical records.
*   **Ingestion**: Python, FeedParser, BeautifulSoup4, yFinance.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10+
*   Docker & Docker Compose
*   Node.js & npm

### 2. One-Command Setup
MarketIntel AI uses a **Master Orchestrator** to handle everything. You do not need to run individual scripts.

```powershell
python run_app.py
```

### 3. What happens next?
*   **Docker DB**: Starts automatically.
*   **Market Discovery**: Seeds all 2,300+ stocks if the DB is empty.
*   **Smart Sync**: Automatically fetches missing history (since last run) for all stocks.
*   **Live Services**: Launches the API, Poller, News Engine, and Dashboard in separate windows.

---

## 📁 Detailed Project Structure

### 🛠️ Core Directories
*   **`/api`**: The backend brain. Powered by **FastAPI**, serving real-time stock data and neural insights. (See **ARCHITECT_HANDBOOK.md** for API Reference).
*   **`/dashboard`**: The visual command center. A **Next.js 14** application with a premium UI.
*   **`/db`**: Database layer. Contains **SQLAlchemy** schema definitions and connection logic.
*   **`/ingestion`**: The data pipeline hub.
    *   `delta_update.py`: Smart-Sync engine for incremental data patching.
    *   `news_aggregator.py`: Rotational engine with integrated **AI Sentiment Scoring**.
    *   `poll_prices.py`: Live price tracker.
*   **`/scripts`**: Production utilities.
    *   `smart_export.py`: High-performance additive export engine for Kaggle (Rows & Columns).

---

## 📜 Maintenance
The platform is designed to be **Zero-Touch**. 
*   **Daily Sync**: Every time you run `run_app.py`, it automatically fills gaps for missing dates.
*   **News Rotation**: The background news service manages its own schedule to ensure 24/7 market coverage.

---
*Built with precision for the modern trader.*
