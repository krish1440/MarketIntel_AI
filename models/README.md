# MarketIntel AI Model Architecture & Registry

This directory contains the decoupled, institutional-grade AI models powering MarketIntel.
Storage is partitioned into **Validation (Out-Of-Sample Holdout)** and **Production (Full-History Refit)**.

---

## 1. Directory Structure

```
models/
├── production/                   <-- Refitted on 100% of historical data (1996 - Present)
│   ├── model0_screener.txt       # Pre-Market Screener & LambdaMART Ranker
│   ├── model1_swing_q10.txt      # Positional Swing Alpha (Quantile 10% downside risk)
│   ├── model1_swing_q50.txt      # Positional Swing Alpha (Quantile 50% median return)
│   ├── model1_swing_q90.txt      # Positional Swing Alpha (Quantile 90% upside target)
│   ├── model2_compounding.txt    # Long-Term Secular Wealth Compounding (>1Y)
│   ├── model3_corridor_p05.txt   # Price Corridor: 5th percentile extreme floor
│   ├── model3_corridor_p25.txt   # Price Corridor: 25th percentile conservative support
│   ├── model3_corridor_p50.txt   # Price Corridor: 50th percentile median drift
│   ├── model3_corridor_p75.txt   # Price Corridor: 75th percentile resistance
│   ├── model3_corridor_p95.txt   # Price Corridor: 95th percentile exhaustion ceiling
│   ├── model4_classifier.joblib  # Universal Stock Action & Platt-Scaled Confidence Classifier
│   └── model_registry.json       # Production schema contracts, feature names & checksums
│
├── validation/                   <-- Used EXCLUSIVELY for out-of-sample scientific auditing
│   ├── weights/                  # Models trained ONLY up to Dec 31, 2023 with 63-day embargo window
│   │   ├── model0_screener.txt
│   │   ├── model1_swing_q10.txt, q50.txt, q90.txt
│   │   ├── model2_compounding.txt
│   │   ├── model3_corridor_p05.txt ... p95.txt
│   │   └── model4_classifier.joblib
│   └── metrics/                  # Realized metrics audited on the 2-Year Test Vault (2024–2026)
│       ├── phase4_audit_master.json   # Multi-model statistical audit report
│       ├── pnl_financial_audit.json   # Realized P&L, Win Rate, Worst Loss %, and Drawdown
│       ├── model0_evaluation.json
│       ├── model1_evaluation.json
│       ├── model2_evaluation.json
│       ├── model3_evaluation.json
│       └── model4_evaluation.json
│
└── active/                       <-- Mirror of production/ for runtime backward compatibility
```

---

## 2. Zero-Leakage Guarantee

* **All 2-Year Out-Of-Sample Backtests and P&L Audits (`pnl_financial_audit.json`) were evaluated using the models in `models/validation/weights/`**.
* The validation models were trained on data ending on **September 28, 2023** (incorporating a strict **63-day Embargo Window** ahead of January 1, 2024).
* The validation models **never saw a single candle from 2024, 2025, or 2026** during training.
* Once the validation proved positive alpha (+25.32% annualized decile spread, 91.38% corridor coverage), the models were refitted on 100% full history into `models/production/` and `models/active/` for live execution in Phase 5.

