# 🧠 MarketIntel AI: Neural Architecture Handbook
**Layer: Machine Learning & Preprocessing**

This folder contains the core machine learning models, architecture definitions, and preprocessing logic that power MarketIntel AI.

---

## 🏛️ Model Architecture

The predictive engine relies on a **Multimodal Fusion Engine** that blends two distinct neural domains:

### 1. The Sequence Engine (LSTM)
*   **File:** `price_lstm.py` (Architecture) & `price_model.py` (Training logic).
*   **Purpose:** Learns temporal dependencies from historical OHLCV data and technical indicators.
*   **Hardware:** Optimized for Intel architectures (IPEX) but fully compatible with CUDA and standard CPU execution.

### 2. The Semantic Engine (Transformers)
*   **File:** `sentiment_model.py`
*   **Purpose:** Utilizes Hugging Face's `DistilBERT` (fine-tuned on SST-2) to read financial news and output a normalized sentiment score (-1.0 to 1.0).
*   **Design:** Operates as a Singleton to prevent duplicate loading of massive transformer weights into memory.

### 3. The Fusion Classifier (XGBoost)
*   **File:** `fusion_model.py`
*   **Purpose:** Acts as the final decision layer. It takes the output from the LSTM and the average sentiment score from DistilBERT, then classifies the final state as `1` (BUY) or `0` (SELL/HOLD).

---

## ⚙️ Data Preprocessing & Features
*   **File:** `preprocess.py`
*   **Purpose:** Contains the industrial technical suite. It automatically injects high-alpha features into raw price data, including:
    *   `SMA_20` & `SMA_50`
    *   `RSI_14` (Relative Strength Index)
    *   `MACD` (Moving Average Convergence Divergence)
    *   `ATR_14` (Volatility)
    *   `Bollinger Bands`
    *   `VWAP`

---

## 🚀 Training Pipelines
*   **`train_price.py`**: Orchestrates the deep learning loop for the LSTM, saving weights to `checkpoints/price_model.pth`.
*   **`train_fusion.py`**: Builds the dataset for the XGBoost classifier, saving the tree structure to `checkpoints/fusion_model.json`.

---
*Maintained by MarketIntel AI Engineering Group.*
