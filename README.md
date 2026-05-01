# 🚀 MarketIntel AI: Total Market Intelligence Engine
**🏆 Kaggle Bronze Medal Dataset Inside**

MarketIntel AI is a production-grade, high-performance market monitoring and prediction platform. It provides **total market coverage** for over 2,300+ stocks across the NSE (National Stock Exchange) and BSE (Bombay Stock Exchange), powered by real-time data, additive history ingestion, and **AI-driven neural sentiment**.

---

## 📊 Institutional Data Source
The raw intelligence powering this platform is derived from our high-density historical dataset:
👉 **[Indian Stock Market: Full 5-Year History (Kaggle)](https://www.kaggle.com/datasets/krishchaudhary14/indian-stock-market-full-5-year-history)**

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
*   **Delta Update Engine**: High-speed incremental fetching that only "patches" missing trading days (idempotent).
*   **Fast Batch Ingestion**: Uses a high-speed 50-stock batch fetching method (5-year history backfill).
*   **Real-Time Poller**: Multi-threaded chunk polling ensures the entire market is tracked every minute.

### 🧠 AI-Driven Intelligence
*   **Transformers Sentiment**: Real-time news analysis using **DistilBERT** to generate market mood scores (-1.0 to 1.0) for every headline.
*   **LSTM Neural Network**: Trained on 4.5M+ historical data points for multi-day price forecasting.
*   **Fusion Signal**: Combines technical indicators (RSI, MACD, etc.) with AI forecasts into a single **BUY/SELL** signal.

---

## 🏗️ Detailed Project Intelligence Map

### 📂 Root: The Command Center
*   **`run_app.py`**: The **Master Orchestrator**. It manages service lifecycle, starts the Docker DB, performs automated syncs, and launches the API/Dashboard in parallel.
*   **`docker-compose.yml`**: Configures the **PostgreSQL 15** environment with persistent volume mapping for 4.5M+ records.
*   **`requirements.txt`**: Strict dependency manifest (Torch-CPU, Transformers, FastAPI, Pandas).
*   **`.gitignore`**: High-performance filtering (ignores `venv/`, large `.csv` exports, and `.pyc` caches).

### 📂 `/api`: The Intelligence Gateway
*   **`main.py`**: The central REST API. Handles fuzzy search, historical snapshots, and real-time neural refresh triggers.
*   **`ARCHITECT_HANDBOOK.md`**: Advanced technical guide for the API logic and neural junction points.

### 📂 `/ingestion`: The Data Heartbeat
*   **`delta_update.py`**: The smart-sync engine. It calculates "data holes" and patches them using a differential-ingestion algorithm.
*   **`news_aggregator.py`**: A rotational scraper that uses **AI Transformers** to analyze news sentiment as it arrives.
*   **`poll_prices.py`**: High-frequency tracker that updates live price snapshots every 60 seconds.
*   **`backfill_history.py`**: Heavy-duty engine for initial 5-year historical data seeding.
*   **`discover_symbols.py`**: The "Mapmaker"—identifies every tradable symbol on the NSE and BSE.

### 📂 `/intelligence`: Prediction Services
*   **`prediction_service.py`**: The bridge between the database and the LSTM model. Handles OHLCV windowing and feature scaling.

### 📂 `/models`: Neural Weights & Logic
*   **`sentiment_model.py`**: Implementation of the **DistilBERT** classifier for financial text analysis.
*   **`train_price.py`**: The training script for the LSTM model using PyTorch.

### 📂 `/db`: Persistence Layer
*   **`schema.py`**: The **SQLAlchemy** blueprint. Defines the relational structure for Stocks, Prices, Quotes, and News.

### 📂 `/scripts`: Production Utilities
*   **`smart_export.py`**: The **Master Export Engine**. Handles high-performance additive exports, merges price matrices, and automates the Kaggle dataset versioning.


---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10+ | Docker & Docker Compose | Node.js & npm

### 2. One-Command Setup
```powershell
python run_app.py
```

### 3. Life-Cycle
*   **Sync**: Every run fills the "weekend gap" automatically.
*   **News**: Background services manage rotation to avoid provider bans.

---

## 📊 Dashboard Access
*   **Institutional Dashboard**: `http://localhost:3000`
*   **Intelligence API (Swagger)**: `http://localhost:8000/docs`

---

## 📜 License
Distributed under the **MIT License**. See `LICENSE` for more information.

---
*Built with precision for the modern trader.*
