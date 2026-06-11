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
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    nse_symbol VARCHAR(20),
    bse_symbol VARCHAR(20)
);

-- -----------------------------------------------------------------------------
-- TABLE: live_quotes
-- DESCRIPTION: Captures real-time price snapshots for dashboard visualization.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS live_quotes (
    id SERIAL PRIMARY KEY,  
    stock_id INTEGER REFERENCES stocks(id),
    exchange VARCHAR(10),
    price DECIMAL(15, 2) NOT NULL,
    change_percent DECIMAL(10, 4),
    volume BIGINT,

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- TABLE: historical_prices
-- DESCRIPTION: Stores multi-year time-series data for analysis and AI training.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historical_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    exchange VARCHAR(10),
    date DATE NOT NULL,
    open DECIMAL(15, 2),
    high DECIMAL(15, 2),
    low DECIMAL(15, 2),
    close DECIMAL(15, 2),
    volume BIGINT,
    UNIQUE (stock_id, exchange, date)
);

-- -----------------------------------------------------------------------------
-- TABLE: news_articles
-- DESCRIPTION: Tracks financial news headlines with AI-generated sentiment metadata.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    published_at TIMESTAMP,
    sentiment_score DECIMAL(10, 4)
);

-- -----------------------------------------------------------------------------
-- TABLE: watchlists
-- DESCRIPTION: Stores user-defined monitoring thresholds for specific stocks.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) UNIQUE,
    target_price_above DECIMAL(15, 2),
    target_price_below DECIMAL(15, 2),
    sentiment_threshold DECIMAL(10, 4),
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- TABLE: alerts
-- DESCRIPTION: Stores the history of triggered alerts for dashboard auditing.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    alert_type VARCHAR(50),
    message TEXT NOT NULL,
    trigger_value DECIMAL(15, 4),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

