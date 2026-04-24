# STACK.md — Technical Stack for Multimodal Stock Intelligence

## Recommendation
We will use a modern, high-performance stack optimized for the local Intel Iris Xe GPU and the specific requirements of Indian markets (BSE/NSE).

## Core Stack

### Backend & AI
- **Language**: Python 3.12+
- **Deep Learning**: **PyTorch 2.5+** with **Intel Extension for PyTorch (IPEX)**.
  - *Rationale*: IPEX provides native optimization for Intel Iris Xe GPUs on Windows via the `xpu` device.
- **Model Architectures**:
  - **Temporal**: LSTM or GRU for historical price patterns.
  - **Semantic**: **DistilBERT** (HuggingFace) for news sentiment analysis.
    - *Rationale*: DistilBERT is faster and lighter than full BERT, making it ideal for integrated GPUs while maintaining 95%+ accuracy.
  - **Fusion**: **XGBoost** as the meta-learner to combine quantitative and qualitative signals.
- **Numerical Processing**: NumPy, Pandas, Scikit-learn.

### Data Acquisition
- **NSE/BSE Live Data**: **`nsepython`** and **`bsedata`**.
  - *Rationale*: These are the most stable community-maintained wrappers for scraping NSE/BSE public APIs.
- **Historical Data**: **`yfinance`**.
  - *Rationale*: Reliable for historical OHLCV data for NSE stocks (using `.NS` suffix).
- **News Aggregation**: **Google News RSS** or targeted scraping of **Moneycontrol/Economic Times**.

### Database
- **Primary DB**: **PostgreSQL**.
  - *Rationale*: Robust relational storage for metadata, user data, and news. Superior to MongoDB for structured financial data and complex queries.
  - **Time-Series Optimization**: We will structure the price table for efficient indexing or use a partitioning strategy to simulate a time-series DB.

### UI & Frontend
- **Design System**: **Stitch MCP**.
- **Framework**: **Vite + Vanilla JS/React** (as per user preference if specified later, defaulting to Vanilla JS for speed).
- **Visuals**: **Moneycontrol-style Dashboard** with high-contrast charts (using Chart.js or Lightweight Charts).

## Hardware Optimization (Intel Iris Xe)
- **Acceleration**: Use `intel_extension_for_pytorch` to move models to `ipex.optimize(model)`.
- **Inference**: Use **OpenVINO** for the sentiment model if inference latency becomes a bottleneck during real-time monitoring.

## Development Tools
- **GSD**: Project management and planning.
- **Git**: Version control.

---
*Confidence: High*
*Last updated: 2026-04-24*
