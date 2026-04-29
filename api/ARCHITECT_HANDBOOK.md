# 🧠 MarketIntel AI: API Architect Handbook
**System Version:** 2.0 (Institutional Intelligence)  
**Status:** High Performance / Production Ready

---

## 📖 1. The Core Philosophy
MarketIntel AI is not just a stock scraper; it is a **Neural Financial Gateway**. The API is designed to solve the "Latency of Intelligence" problem—the gap between raw market movements and actionable insight. 

We bridge three distinct worlds:
1.  **The Database (SQLAlchemy):** Stable, relational storage for 4.5M+ records.
2.  **The Real-World (YFinance/RSS):** High-velocity, raw data streams.
3.  **The Neural Stack (Transformers/LSTM):** Where raw numbers turn into sentiment and predictions.

---

## 🏗️ 2. Architectural Blueprint
The API follows a **Non-Blocking Orchestration** pattern. Instead of waiting for massive data syncs to finish, the API serves cached "Neural Snapshots" while background workers (`delta_update.py`) patch the gaps in the dark.

### **The Neural Junction**
Every time a user requests a stock detail, the API doesn't just read a row. It triggers a **Synthetic Intelligence Loop**:
*   **Sentiment Hook:** Scans the latest RSS headlines and runs them through a DistilBERT Transformer to generate a live market mood score.
*   **Prediction Hook:** Feeds historical OHLCV data into a trained LSTM model to output a "Next-Step" price forecast.

---

## 📡 3. High-Traffic Endpoint Strategy

### `GET /api/stocks`
**The Discovery Engine.**  
Designed for sub-100ms response times. It uses a **Paginated Matrix** approach to deliver a broad overview of the 2,361-ticker universe without overloading the browser's DOM.

### `GET /api/stock/{ticker}`
**The Deep Intelligence Node.**  
This is our most complex endpoint. It merges:
1.  **Core Metadata:** Name, Ticker, Exchange.
2.  **Market Dynamics:** Current Price, Daily Change.
3.  **Historical Array:** The last 100 days of price movement (OHLCV).
4.  **Live News Feed:** Real-time headlines + **AI Sentiment Scores**.
5.  **Neural Forecast:** The calculated price prediction for the next session.

---

## 🛡️ 4. Resilience & Reliability (The "Safety Valves")

### **The NaN Guard (`clean_nas`)**
Financial data is messy. APIs often crash on `NaN` (Not a Number) values from broken feed data. Our API uses a recursive `clean_nas` filter that sanitizes every JSON response, ensuring the frontend never sees a "Hydration Error" or "Value Type" crash.

### **Lazy-Loading AI**
The `PredictionService` and `SentimentExpert` follow a **Singleton Pattern**. We don't reload the models for every request; we keep them hot in memory, drastically reducing the "Time to First Insight."

---

## 🚀 5. Developer Onboarding
If you are modifying this API, remember the **Golden Rule of MarketIntel**:  
*"The User comes first, the Data second, and the AI third."* 

Always ensure the endpoint returns a valid UI response immediately, even if the AI or Sync Engine is still "thinking" in the background.

---

**© 2026 MarketIntel AI Operations Group**  
*Built for the next generation of algorithmic intelligence.*
