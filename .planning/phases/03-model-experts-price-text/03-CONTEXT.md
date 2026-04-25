# Phase 3: Model Experts (Price & Text) - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase develops the "brain" of the system: two specialized AI models. One model handles temporal patterns in stock prices (LSTM), and the other handles semantic sentiment in financial news (DistilBERT). Both models will be optimized for the Intel Iris Xe GPU.

</domain>

<decisions>
## Implementation Decisions

### Price Model (LSTM)
- **Architecture**: Multi-layer LSTM with Dropout for regularization.
- **Features**: Close price, Volume, SMA(20), RSI(14), MACD.
- **Target**: Next day's closing price or movement direction.
- **Acceleration**: Use `ipex.optimize()` on the model and optimizer.

### Sentiment Model (DistilBERT)
- **Model**: `distilbert-base-uncased-finetuned-sst-2-english` (pre-trained on sentiment).
- **Task**: Classify news headlines/summaries as Positive, Negative, or Neutral.
- **Output**: A sentiment score (e.g., probability of positive class).

### Training Strategy
- **Incremental Learning**: Design the training loop to support updating models with new data (important for v2 requirements).
- **Validation**: Use a 80/20 time-based split for training and testing.

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/STACK.md` (Intel IPEX details)
- `.planning/research/ARCHITECTURE.md` (Fusion model overview)

</canonical_refs>

<specifics>
## Specific Ideas
- Create `models/price_model.py` and `models/sentiment_model.py`.
- Create a `models/train.py` script that handles the training pipeline for both.

</specifics>

---
*Phase: 03-model-experts-price-text*
*Context gathered: 2026-04-25*
