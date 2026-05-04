# 🌌 MarketIntel AI: Institutional Project Handbook
**Master Repository Architecture & Operational Guide**

MarketIntel AI is a full-stack, autonomous market intelligence platform designed for high-density analysis of the Indian Stock Market. It leverages multimodal AI (LSTM + Transformers + XGBoost) to generate real-time trading signals and sentiment-aware market monitoring.

---

## 🏛️ Ecosystem Overview

The platform is structured into five core architectural layers:

### 1. 🛰️ Ingestion Layer (`ingestion/`)
*   **Purpose**: Handles real-time and historical data acquisition.
*   **Tech**: yfinance, nsepython, feedparser.
*   **Handbook**: [INGESTION_DOCUMENTATION.md](file:///d:/PROJECT/Ai-STOCK-Market/ingestion/INGESTION_DOCUMENTATION.md)

### 2. 🗄️ Persistence Layer (`db/`)
*   **Purpose**: Manages the PostgreSQL relational engine and SQLAlchemy ORM.
*   **Tech**: PostgreSQL 16, SQLAlchemy.
*   **Handbook**: [DATABASE_DOCUMENTATION.md](file:///d:/PROJECT/Ai-STOCK-Market/db/DATABASE_DOCUMENTATION.md)

### 3. 🧠 Neural Layer (`models/`)
*   **Purpose**: Contains the AI architectures and training pipelines.
*   **Tech**: PyTorch, DistilBERT, XGBoost, Intel IPEX.
*   **Handbook**: [MODELS_HANDBOOK.md](file:///d:/PROJECT/Ai-STOCK-Market/models/MODELS_HANDBOOK.md)

### 4. ⚡ Intelligence Layer (`intelligence/`)
*   **Purpose**: Houses the high-level decision daemons and inference services.
*   **Tech**: Singleton Inference Engines, Auto-Learner Daemons.
*   **Handbook**: [INTELLIGENCE_HANDBOOK.md](file:///d:/PROJECT/Ai-STOCK-Market/intelligence/INTELLIGENCE_HANDBOOK.md)

### 5. 🖥️ Presentation Layer (`api/` & `dashboard/`)
*   **Purpose**: Provides the RESTful interface and the Next.js visual terminal.
*   **Tech**: FastAPI, Next.js 15, TailwindCSS.
*   **Handbooks**: [ARCHITECT_HANDBOOK.md](file:///d:/PROJECT/Ai-STOCK-Market/api/ARCHITECT_HANDBOOK.md) & [DASHBOARD_HANDBOOK.md](file:///d:/PROJECT/Ai-STOCK-Market/dashboard/DASHBOARD_HANDBOOK.md)

---

## 🚀 Quick Start (Production Setup)

The entire ecosystem is managed by a single orchestrator:

```powershell
# 1. Initialize environment
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 2. Launch everything (DB, API, Dashboard, Daemons)
python run_app.py
```

---

## 🛠️ Infrastructure & Config
*   **`docker-compose.yml`**: Configures the PostgreSQL 16 container on port 5433.
*   **`.env`**: Contains environment-specific credentials and API keys.
*   **`requirements.txt`**: Definitive list of institutional-grade dependencies.

---
*Developed with excellence by the MarketIntel AI Group.*
