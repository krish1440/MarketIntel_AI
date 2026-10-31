# Phase 2: Local Medallion Lakehouse & Vectorized Polars Feature Engine

## 1. Objectives & Scope
- **Medallion Architecture on Local Disk**: Implement zero-cloud-cost Bronze $\rightarrow$ Silver $\rightarrow$ Gold directory layout.
- **Macro & Sector Relative Strength (Non-Price Data)**:
  - Backfill and store all 16 official NSE Sectoral Indices (`^CNXIT`, `^NSEBANK`, `^CNXAUTO`, etc.) and `^INDIAVIX` from inception to present.
  - Implement `SectorMapper` to map all 2,357 stocks to their sectors with guaranteed **0% Nulls** (using Broad Benchmark fallbacks).
- **Vectorized Technical Indicator Engine**: Ultra-fast Rust-based Polars computation of:
  - Moving Averages: EMA (9, 21, 50, 200), SMA (20, 50).
  - Volatility & Range: ATR (14), Bollinger Bands (20, 2), Keltner Channels, India VIX regime.
  - Momentum & Trend: Supertrend (10, 3), MACD (12, 26, 9), RSI (14), Sector Relative Strength (20d).
  - Volume & Liquidity: VWAP, Volume 20 SMA, On-Balance Volume (OBV).
- **Candlestick Structure Vectorization**: Encode candlestick geometry (body ratio, upper shadow, lower shadow, gap vs ATR) for instant ML ingestion without image conversion.
- **DuckDB Analytical Query Engine**: Sub-second SQL querying across partitioned Parquet files with partition pruning.

## 2. Technical Contracts & Schemas

### Decoupled Gold Feature Store Architecture (Model-Specific):
```
/data/lakehouse/gold/
├── features_screener_ranking/     # Model 0: Cross-sectional pre-market rank (Momentum, VCP, Volume)
├── features_short_term_intraday/  # Model 1: Micro-timing 1m/5m (VWAP, Supertrend, RSI, Wick/Body ratios)
├── features_long_term_swing/      # Model 2: Positional Daily (50/200 EMA, 60d Sector RS, Delivery %, FII/DII)
└── features_price_corridor/       # Model 3: Quantile Regression & Monte Carlo Drift (P10, P50, P90)
```

### Global Macro & Cross-Asset Features (Stored in Silver):
- `SP500` (`^GSPC`): 24,826 daily bars (1927 - Present)
- `NASDAQ100` (`^IXIC`): 14,052 daily bars (1971 - Present, leads Indian IT)
- `CRUDE_OIL` (`CL=F`): 6,576 daily bars (2000 - Present, margin factor)
- `USD_INR` (`INR=X`): 5,944 daily bars (2003 - Present, FII currency flow)
- `US10Y_YIELD` (`^TNX`): 16,196 daily bars (1962 - Present, risk-on/off)

### Silver OHLCV + Technical Schema:
| Column | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | Datetime (UTC/IST) | Candle open timestamp |
| `symbol` | String | Scrip Symbol |
| `open`, `high`, `low`, `close` | Float32 | Adjusted price levels |
| `volume` | Int64 | Traded volume |
| `delivery_qty` | Int64 | Delivery volume (for daily) |
| `delivery_pct` | Float32 | Delivery percentage |
| `vwap` | Float32 | Volume-Weighted Average Price |
| `ema_9`, `ema_21`, `ema_50`, `ema_200` | Float32 | Exponential moving averages |
| `supertrend`, `supertrend_direction` | Float32, Int8 | Supertrend (10, 3) |
| `rsi_14` | Float32 | Relative Strength Index |
| `macd`, `macd_signal`, `macd_hist` | Float32 | MACD indicators |
| `atr_14` | Float32 | Average True Range |
| `bb_upper`, `bb_middle`, `bb_lower` | Float32 | Bollinger Bands (20, 2) |
| `candle_body_ratio`, `upper_shadow_ratio`, `lower_shadow_ratio` | Float32 | Candlestick geometry features |

## 3. Implementation Steps & Milestones
- [ ] Step 2.1: Implement local Medallion filesystem manager (Bronze/Silver/Gold directory initializer).
- [ ] Step 2.2: Implement Polars-based vectorized technical indicator calculator.
- [ ] Step 2.3: Implement candlestick anatomy and price-action feature extraction.
- [ ] Step 2.4: Build DuckDB analytical query layer with automated partition pruning.
- [ ] Step 2.5: Benchmark processing speed across 1,000,000+ historical bars.

