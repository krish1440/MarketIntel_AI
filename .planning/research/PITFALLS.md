# PITFALLS.md — Potential Risks & Prevention

## 1. Data Integrity & Scraping
- **Risk**: NSE/BSE public APIs are non-official and can change or block IPs.
- **Prevention**: 
  - Implement robust error handling and retries.
  - Use rotating User-Agents.
  - Implement aggressive caching of non-volatile data.

## 2. Lookahead Bias
- **Risk**: Training the model on future data (e.g., using tomorrow's high to predict today's movement).
- **Prevention**: Strict validation splits using time-based slicing. Never shuffle data before splitting.

## 3. News Sentiment Noise
- **Risk**: Clickbait or redundant news titles can skew sentiment.
- **Prevention**: 
  - Deduplication of news based on title similarity.
  - Weighting sentiment by source reliability or volume.

## 4. Hardware Limitations (Intel Iris Xe)
- **Risk**: Large models (like BERT-Large) will be extremely slow to train.
- **Prevention**: 
  - Use **DistilBERT** or **TinyBERT**.
  - Use **Intel IPEX** for `xpu` acceleration.
  - Leverage **Mixed Precision (BF16)** training if supported.

## 5. Over-fitting to Market Volatility
- **Risk**: Models might perform well in bull markets but fail during corrections.
- **Prevention**: 
  - Include "Market Regime" indicators (VIX, overall index trend) in the XGBoost meta-learner.
  - Implement a "Confidence Score" so the system can say "I don't know" during high uncertainty.

---
*Last updated: 2026-04-24*
