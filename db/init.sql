-- Initial schema for Stock Market Intelligence System

CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    exchange VARCHAR(10) NOT NULL -- 'NSE' or 'BSE'
);

CREATE TABLE IF NOT EXISTS live_quotes (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    price DECIMAL(15, 2) NOT NULL,
    change_percent DECIMAL(10, 4),
    volume BIGINT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historical_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date DATE NOT NULL,
    open DECIMAL(15, 2),
    high DECIMAL(15, 2),
    low DECIMAL(15, 2),
    close DECIMAL(15, 2),
    volume BIGINT,
    UNIQUE (stock_id, date)
);

CREATE INDEX IF NOT EXISTS idx_historical_prices_stock_date ON historical_prices(stock_id, date);

-- Pre-populate with some major stocks
INSERT INTO stocks (ticker, name, exchange) VALUES 
('RELIANCE', 'Reliance Industries Ltd.', 'NSE'),
('TCS', 'Tata Consultancy Services Ltd.', 'NSE'),
('HDFCBANK', 'HDFC Bank Ltd.', 'NSE'),
('ICICIBANK', 'ICICI Bank Ltd.', 'NSE'),
('INFY', 'Infosys Ltd.', 'NSE'),
('RELIANCE', 'Reliance Industries Ltd.', 'BSE'),
('500325', 'Reliance Industries Ltd.', 'BSE')
ON CONFLICT (ticker) DO NOTHING;
