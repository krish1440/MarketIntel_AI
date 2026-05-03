# 🧠 MarketIntel AI: Intelligence Core
**Layer: Deep Learning & Autonomous Systems**

This folder contains the true "Brain" of the MarketIntel AI platform. It handles everything from continuous model fine-tuning to real-time, multimodal predictions.

---

## 🏛️ Architecture Overview

The Intelligence Core relies on three primary components to turn raw market data into actionable trading signals:

1.  **Autonomous Polling (`auto_learner.py`)**: A background daemon that tracks database growth. It automatically detects when substantial new data points are ingested and triggers background retraining without manual intervention.
2.  **Incremental Finetuning (`incremental_learner.py`)**: Designed for high performance and low computational overhead. Instead of retraining massive XGBoost and LSTM structures from scratch, this engine slices the newest data and performs "tree-level" updates.
3.  **Neural Pipeline (`prediction_service.py`)**: The central routing service. It extracts technical indicators, queries sentiment scores from the database, and injects everything into a multimodal fusion model (LSTM + Transformers + XGBoost) to generate a unified `BUY`/`SELL`/`HOLD` signal and multi-day price forecast.

---

## 🚀 Key Technologies

*   **PyTorch**: Used for deep sequence learning (LSTM) on multi-dimensional OHLCV sequences.
*   **XGBoost**: For incremental "Gradient Boosted" tree updates across fusion datasets.
*   **Pandas & NumPy**: For high-speed matrix windowing and technical indicator generation (RSI, MACD, SMA).

---

## ⚙️ How it Connects to the API

The `PredictionService` operates as a **Singleton** initialized by the FastAPI gateway (`api/main.py`).

*   It stays resident in memory to ensure inference speed is not bottlenecked by model loading times.
*   It utilizes our `clean_nas` safety philosophy ensuring no neural layer passes a `NaN` back to the frontend.
*   It provides advanced multi-day drift predictions used by charting libraries to plot the "Forecast Cone."

---
*Maintained by MarketIntel AI Engineering Group.*
