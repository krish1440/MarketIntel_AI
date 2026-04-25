# Phase 4: Multimodal Fusion & Intelligence - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase integrates the individual AI experts into a single cohesive "multimodal" intelligence engine. It uses a "Late Fusion" strategy where the outputs of the LSTM and DistilBERT models are combined by a meta-learner (XGBoost) to produce a final, more accurate prediction.

</domain>

<decisions>
## Implementation Decisions

### Meta-Learner (XGBoost)
- **Model**: `XGBClassifier` or `XGBRegressor` (based on whether we want direction or price).
- **Features**: 
  - LSTM Prediction (next-day price delta).
  - Sentiment Score (24h rolling average).
  - Volatility Index (if available) or standard deviation of recent returns.
- **Training**: Train on historical overlaps where both price data and news data exist.

### Intelligence Engine
- **Component**: `models/fusion_model.py`.
- **Inference**: A unified function `get_multimodal_signal(stock_id)` that:
  1. Pulls recent news sentiment.
  2. Pulls recent price sequences.
  3. Feeds them through experts.
  4. Passes expert outputs to XGBoost.
  5. Returns a "Buy/Sell/Hold" signal + Confidence score.

### Incremental Learning
- Implementation of a "re-fit" logic in `models/fusion_model.py` to allow the system to learn from its recent mistakes without full retraining.

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/ARCHITECTURE.md` (Late fusion diagram)
- `.planning/REQUIREMENTS.md` (INTL-03, SYS-01)

</canonical_refs>

<specifics>
## Specific Ideas
- Implement a `prediction_service.py` that can be queried by the UI in the next phase.

</specifics>

---
*Phase: 04-multimodal-fusion-intelligence*
*Context gathered: 2026-04-25*
