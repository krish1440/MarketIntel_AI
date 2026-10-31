# Phase 3: Real-Time In-Memory Bus & Time-Series Serving DB

## 1. Objectives & Scope
- **Redis High-Throughput In-Memory Caching**:
  - `Redis Hashes`: $O(1)$ live ticker lookup table (`quote:{exchange}:{symbol}`) for all 2,000+ stocks under 15MB RAM.
  - `Redis Streams`: High-speed tick buffer with a fixed ring size (`stream:ticks:{exchange}`).
  - `Redis Pub/Sub`: Low-latency broadcast channel to active web clients.
- **Fast Time-Series Serving DB**:
  - Setup **TimescaleDB** or **ClickHouse Local** with monthly chunked hypertables.
  - Sub-30ms query latency for 1-minute, 5-minute, 1-hour, and 1-day candlestick charts.
- **Streaming Bar Aggregator**:
  - Ingests real-time tick feeds from broker WebSockets.
  - Aggregates ticks on the fly into 1-minute and 5-minute candles in real time.
  - Persists completed candles into the Silver Lakehouse and Serving DB asynchronously.

## 2. Technical Contracts & Schemas

### Redis Data Structures:
- **Ticker Hash**: `HSET quote:NSE:RELIANCE ltp 2950.50 open 2930.00 high 2965.00 low 2925.00 vwap 2945.20 volume 5230000 change_pct 0.70 updated_at 1718000000`
- **Tick Stream**: `XADD stream:ticks:NSE * symbol RELIANCE price 2950.50 qty 50 trade_time 1718000000`
- **PubSub Channel**: `live_feed` (JSON broadcast to FastAPI WebSockets).

### Time-Series Hypertable Schema:
```sql
CREATE TABLE candles_1m (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume BIGINT NOT NULL,
    vwap REAL
);
SELECT create_hypertable('candles_1m', 'time', chunk_time_interval => INTERVAL '1 month');
CREATE INDEX idx_candles_1m_sym_time ON candles_1m (symbol, time DESC);
```

## 3. Implementation Steps & Milestones
- [ ] Step 3.1: Set up Redis connection pool and caching manager (Hashes, Streams, Pub/Sub).
- [ ] Step 3.2: Initialize TimescaleDB / ClickHouse Local hypertable schemas.
- [ ] Step 3.3: Build real-time streaming tick aggregator (tick-to-candle engine).
- [ ] Step 3.4: Build asynchronous write-behind worker from Redis Streams to Bronze/Silver Parquet.
- [ ] Step 3.5: Verify sub-30ms query response time for 5,000+ candle history requests.

