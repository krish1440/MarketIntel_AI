/*
 * MARKETINTEL AI: CORE DATABASE SCHEMA
 * =====================================
 *
 * This SQL script initializes the relational database for the MarketIntel AI platform.
 * It is designed for PostgreSQL 16+ and is automatically executed by the 
 * docker-entrypoint-initdb.d mechanism during container startup.
 *
 * SCHEMA OVERVIEW:
 * 1. stocks: Master asset registry.
 * 2. live_quotes: High-frequency price snapshots.
 * 3. historical_prices: Time-series OHLCV data.
 * 4. news_articles: Sentiment-aware news metadata.
 *
 * MAINTAINER: MarketIntel AI Intelligence Team
 * VERSION: 1.1.0
 */

-- -----------------------------------------------------------------------------
-- TABLE: stocks
-- DESCRIPTION: Stores the core registry of tradable equity assets.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    -- Unique ticker identifier (e.g., 'RELIANCE', 'TCS').
    ticker VARCHAR(20) UNIQUE NOT NULL,
    -- Full legal name of the corporation.
    name VARCHAR(100),
    -- Yahoo Finance / Exchange symbol for NSE (e.g., 'RELIANCE.NS').
    nse_symbol VARCHAR(20),
    -- Yahoo Finance / Exchange symbol for BSE (e.g., 'RELIANCE.BO').
    bse_symbol VARCHAR(20)
);

-- -----------------------------------------------------------------------------
-- TABLE: live_quotes
-- DESCRIPTION: Captures real-time price snapshots for dashboard visualization.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS live_quotes (
    id SERIAL PRIMARY KEY,
    -- Reference to the parent stock in the 'stocks' table.
    stock_id INTEGER REFERENCES stocks(id),
    -- The source exchange for this quote ('NSE' or 'BSE').
    exchange VARCHAR(10),
    -- Current market price with 2-decimal precision.
    price DECIMAL(15, 2) NOT NULL,
    -- Intraday percentage change from previous close.
    change_percent DECIMAL(10, 4),
    -- Total traded volume in the current session.
    volume BIGINT,
    -- Timestamp of record creation (UTC).
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- TABLE: historical_prices
-- DESCRIPTION: Stores multi-year time-series data for analysis and AI training.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historical_prices (
    id SERIAL PRIMARY KEY,
    -- Reference to the parent stock.
    stock_id INTEGER REFERENCES stocks(id),
    -- The source exchange for this price point.
    exchange VARCHAR(10),
    -- The specific trading date.
    date DATE NOT NULL,
    -- OHLCV Data Points
    open DECIMAL(15, 2),
    high DECIMAL(15, 2),
    low DECIMAL(15, 2),
    close DECIMAL(15, 2),
    volume BIGINT,
    -- UNIQUE CONSTRAINT: Prevents duplicate time-series entries during sync.
    UNIQUE (stock_id, exchange, date)
);

-- -----------------------------------------------------------------------------
-- TABLE: news_articles
-- DESCRIPTION: Tracks financial news headlines with AI-generated sentiment metadata.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    -- Reference to the related stock asset.
    stock_id INTEGER REFERENCES stocks(id),
    -- The article headline.
    title TEXT NOT NULL,
    -- A brief summary of the article content.
    summary TEXT,
    -- Unique URL for the article (acts as an idempotency key).
    url TEXT UNIQUE NOT NULL,
    -- Publication timestamp.
    published_at TIMESTAMP,
    -- AI-Generated Sentiment Score: -1.0 (Bearish) to 1.0 (Bullish).
    sentiment_score DECIMAL(10, 4)
);

-- -----------------------------------------------------------------------------
-- SEED DATA: CORE EQUITIES
-- DESCRIPTION: Pre-populates the database with blue-chip Indian stocks to 
--              ensure system functionality upon initial deployment.
-- -----------------------------------------------------------------------------
INSERT INTO stocks (ticker, name, nse_symbol, bse_symbol) VALUES 
('RELIANCE', 'Reliance Industries Ltd.', 'RELIANCE.NS', 'RELIANCE.BO'),
('TCS', 'Tata Consultancy Services Ltd.', 'TCS.NS', 'TCS.BO'),
('HDFCBANK', 'HDFC Bank Ltd.', 'HDFCBANK.NS', 'HDFCBANK.BO'),
('INFY', 'Infosys Ltd.', 'INFY.NS', 'INFY.BO'),
('ICICIBANK', 'ICICI Bank Ltd.', 'ICICIBANK.NS', 'ICICIBANK.BO')
ON CONFLICT (ticker) DO UPDATE SET 
    nse_symbol = EXCLUDED.nse_symbol,
    bse_symbol = EXCLUDED.bse_symbol;

