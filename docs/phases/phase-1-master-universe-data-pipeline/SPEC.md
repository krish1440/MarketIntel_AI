# Phase 1: Master Security Universe & Historical Data Ingestion Pipeline

## 1. Objectives & Scope
- **Dual-Exchange Mapping**: Link NSE (~2,250 equities) and BSE (~5,400 equities) using ISIN as the universal golden key.
- **Master Universe Database**: Store complete metadata (ISIN, NSE Symbol, BSE Code/ID, Company Name, Sector, Industry, Market Cap Category, Primary Exchange).
- **Deep Historical Backfill (EOD)**:
  - Official NSE & BSE Bhavcopy crawler for 2000–present daily bars including delivery quantity and delivery percentage.
  - Multi-threaded `yfinance` bulk backfill for adjusted OHLCV data.
- **Intraday Historical Bars (1m / 5m)**:
  - Free Broker API connectors (DhanHQ / Angel One SmartAPI / Shoonya) to paginate and fetch 1–3 years of 1-minute historical candles.

## 2. Technical Contracts & Schemas

### Master Security Schema:
```sql
CREATE TABLE master_securities (
    isin VARCHAR(12) PRIMARY KEY,
    nse_symbol VARCHAR(30),
    bse_code VARCHAR(10),
    bse_id VARCHAR(30),
    company_name VARCHAR(255) NOT NULL,
    macro_sector VARCHAR(100),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap_tier VARCHAR(20), -- LargeCap, MidCap, SmallCap, MicroCap
    is_active BOOLEAN DEFAULT TRUE,
    primary_exchange VARCHAR(5) DEFAULT 'NSE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_nse_symbol ON master_securities(nse_symbol);
CREATE INDEX idx_bse_code ON master_securities(bse_code);
```

### Bronze Lakehouse File Structure:
- `/data/lakehouse/bronze/master/securities_master.parquet`
- `/data/lakehouse/bronze/bhavcopy/year=YYYY/month=MM/bhav_YYYYMMDD.parquet`
- `/data/lakehouse/bronze/intraday_raw/{exchange}/{symbol}/year=YYYY/data.parquet`

## 3. Implementation Steps & Milestones
- [x] Step 1.1: Download and parse official NSE `EQUITY_L.csv` and Angel One Scrip Master.
- [x] Step 1.2: Build ISIN reconciliation engine to generate clean `securities_master.parquet` (2,357 active equities mapped across NSE and BSE).
- [x] Step 1.3: Build Angel One SmartAPI automated TOTP client connected to `https://apiconnect.angelone.in`.
- [x] Step 1.4: Build `yfinance` multi-decade bulk backfill worker (`period='max'`) with parallel multi-threading and Parquet partitioning.
- [x] Step 1.5: Complete full universe inception-to-date backfill (2,353 stocks saved, 187.61 MB on disk).
- [x] Step 1.6: Build broker API historical 1-minute candle downloader for Focus Universe (verified on RELIANCE and TCS).
- [x] Step 1.7: Build fast Daily Incremental Sync engine (`daily_sync.py`) with zero-RAM automated scheduler support.
- [x] Step 1.8: Build 1-Year 1-Minute Intraday Backfill Engine (`scripts/bulk_intraday_backfill.py`) with monthly pagination, rate-limiting (3 req/s), auto-checkpointing, and 5-minute resampling.
- [x] Step 1.9: Build Unified Non-Price Engine (`scripts/run_all_non_price_pipeline.py`) covering 16 Sector Indices, India VIX, FII/DII net flows, NSE Delivery %, and Corporate Calendar.

