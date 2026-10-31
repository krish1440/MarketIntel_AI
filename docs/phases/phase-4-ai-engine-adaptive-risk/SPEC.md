# Phase 4: Dual-Model AI Intelligence & Adaptive Risk Engine

## 1. Objectives & Scope
The platform implements a **Dual-Model Architecture** separating Short-Term (Intraday/Quick Swing) from Long-Term (Positional/Investment) decision-making:

### Model 1: Short-Term Micro-Timing & Intraday Engine
- **Trading Horizon**: Intraday (15-min to EOD 15:15 IST) and Quick Swings (1–3 days).
- **Timeframes Analyzed**: 1-minute and 5-minute candles.
- **Input Features**:
  - VWAP band deviations and Volume spikes.
  - 5-minute Supertrend (10, 3) flips and 9/21 EMA slope momentum.
  - Candlestick anatomy ratios (body ratio, upper/lower shadows, gap vs ATR).
  - Intraday RSI (14) momentum and divergence.
- **Execution Target**: Quick directional probability ($\mathcal{P}(\text{Buy})$, $\mathcal{P}(\text{Hold})$, $\mathcal{P}(\text{Sell})$), tight ATR trailing stop-loss, and rapid 1.5R partial profit taking.

### Model 2: Long-Term Positional & Swing Investment Engine
- **Trading Horizon**: Multi-Week Swing (1–4 weeks) and Multi-Month Positional Investment (1–12 months).
- **Timeframes Analyzed**: Daily (1D) and Weekly bars.
- **Input Features**:
  - 50-day and 200-day EMA structural trends (Golden/Death Cross).
  - Sector Relative Strength (RS) vs NIFTY 50 over 20, 60, and 120 days.
  - Institutional accumulation signals: Multi-day Delivery Volume % spikes ($>1.5\sigma$ above 30-day mean).
  - Distance from 52-week High / Low and Volatility Contraction Patterns (VCP).
- **Execution Target**: Positional trend strength, multi-month profit targets (3R–5R), and Monte Carlo 1-year probabilistic price corridors (P10, P50, P90).

---

## 2. Technical Contracts & Schemas

### Dual-Model AI Payload Schema:
```json
{
  "symbol": "RELIANCE",
  "timestamp": "2026-10-31T09:45:00+05:30",
  "short_term_model": {
    "horizon": "Intraday / 1-3 Days",
    "signal": "BUY",
    "confidence": 0.81,
    "probabilities": {"buy": 0.81, "hold": 0.13, "sell": 0.06},
    "trigger_candle": "5-minute",
    "entry_price": 1162.50,
    "dynamic_stop_loss": 1154.00,
    "target_1_scalp": 1175.25,
    "trailing_strategy": "Supertrend(10,3) on 5m",
    "shap_drivers": [
      {"feature": "vwap_cross", "impact": "+16%", "desc": "Price reclaimed VWAP with 2.4x volume surge"},
      {"feature": "supertrend_bullish", "impact": "+11%", "desc": "Bullish 5m Supertrend flip"}
    ]
  },
  "long_term_model": {
    "horizon": "Swing / 1-6 Months",
    "signal": "ACCUMULATE / BUY",
    "confidence": 0.74,
    "probabilities": {"buy": 0.74, "hold": 0.20, "sell": 0.06},
    "macro_trend": "BULLISH_CONTINUATION",
    "positional_stop_loss": 1120.00,
    "target_1_swing": 1240.00,
    "target_2_investment": 1350.00,
    "delivery_accumulation": "HIGH (58.4% delivery over 5 days)",
    "sector_relative_strength": "Energy sector outperforming Nifty by +2.1%",
    "price_corridor_1_year": {
      "p10_floor": 1080.00,
      "p50_median": 1280.00,
      "p90_bull_ceiling": 1420.00
    }
  }
}
```

## 3. Implementation Steps & Milestones
- [ ] Step 4.1: Build Pre-Market Screener ranking engine.
- [ ] Step 4.2: Build feature extraction pipeline for Focus List stocks.
- [ ] Step 4.3: Train and calibrate LightGBM/XGBoost directional classifier with probability calibration (Platt Scaling).
- [ ] Step 4.4: Integrate TreeSHAP for real-time feature attribution.
- [ ] Step 4.5: Implement ATR-based dynamic risk calculator and 1% risk position sizing.
- [ ] Step 4.6: Implement Quantile Regression / Monte Carlo price corridor generator.

