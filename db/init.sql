-- Modernized Schema for Stock Market Intelligence System
-- Matches SQLAlchemy models in db/schema.py

CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    nse_symbol VARCHAR(20),
    bse_symbol VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS live_quotes (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    exchange VARCHAR(10),
    price DECIMAL(15, 2) NOT NULL,
    change_percent DECIMAL(10, 4),
    volume BIGINT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    published_at TIMESTAMP,
    sentiment_score DECIMAL(10, 4)
);

-- Pre-populate with major stocks using verified symbols
INSERT INTO stocks (ticker, name, nse_symbol, bse_symbol) VALUES 
('RELIANCE', 'Reliance Industries Ltd.', 'RELIANCE.NS', 'RELIANCE.BO'),
('TCS', 'Tata Consultancy Services Ltd.', 'TCS.NS', 'TCS.BO'),
('HDFCBANK', 'HDFC Bank Ltd.', 'HDFCBANK.NS', 'HDFCBANK.BO'),
('INFY', 'Infosys Ltd.', 'INFY.NS', 'INFY.BO'),
('ICICIBANK', 'ICICI Bank Ltd.', 'ICICIBANK.NS', 'ICICIBANK.BO')
ON CONFLICT (ticker) DO UPDATE SET 
    nse_symbol = EXCLUDED.nse_symbol,
    bse_symbol = EXCLUDED.bse_symbol;
