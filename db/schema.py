"""
MarketIntel AI: Database Schema and Persistence Layer
=====================================================

This module defines the relational mapping (ORM) for the entire MarketIntel 
AI ecosystem using SQLAlchemy. It establishes the schema for stocks, price
history, real-time quotes, news sentiment, watchlists, and triggered alerts.
"""
from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, BIGINT, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Stock(Base):
    """Represents a unique equity in the Indian Stock Market universe."""
    __tablename__ = 'stocks'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), unique=True, nullable=False) # Base ticker (e.g. RELIANCE)
    name = Column(String(100))
    nse_symbol = Column(String(20)) # e.g. RELIANCE.NS
    bse_symbol = Column(String(20)) # e.g. 500325.BO
    
    # Fundamental Data
    pe_ratio = Column(DECIMAL(10, 2), nullable=True)
    market_cap = Column(BIGINT, nullable=True)
    eps = Column(DECIMAL(10, 2), nullable=True)
    revenue_growth = Column(DECIMAL(10, 4), nullable=True)
    debt_to_equity = Column(DECIMAL(10, 4), nullable=True)
    sector = Column(String(50), nullable=True)

class LiveQuote(Base):
    """Stores high-frequency price snapshots for active market monitoring."""
    __tablename__ = 'live_quotes'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    exchange = Column(String(10)) # NSE or BSE
    price = Column(DECIMAL(15, 2), nullable=False)
    change_percent = Column(DECIMAL(10, 4))
    volume = Column(BIGINT)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class HistoricalPrice(Base):
    """Archival storage for daily OHLCV data points used for AI training."""
    __tablename__ = 'historical_prices'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    exchange = Column(String(10)) # NSE or BSE
    date = Column(Date, nullable=False)
    open = Column(DECIMAL(15, 2))
    high = Column(DECIMAL(15, 2))
    low = Column(DECIMAL(15, 2))
    close = Column(DECIMAL(15, 2))
    volume = Column(BIGINT)

class NewsArticle(Base):
    """Container for scraped news data and its associated neural sentiment score."""
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    title = Column(String, nullable=False)
    summary = Column(String)
    url = Column(String, unique=True, nullable=False)
    published_at = Column(DateTime)
    sentiment_score = Column(DECIMAL(10, 4), nullable=True)

class HistoricalFundamentals(Base):
    """Time-series storage for fundamental metrics to track valuation trends."""
    __tablename__ = 'historical_fundamentals'
    __table_args__ = (UniqueConstraint('stock_id', 'date', name='_stock_date_uc'),)
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    date = Column(Date, default=datetime.date.today)
    pe_ratio = Column(DECIMAL(10, 2))
    eps = Column(DECIMAL(10, 2))
    market_cap = Column(BIGINT)
    revenue_growth = Column(DECIMAL(10, 4))
    debt_to_equity = Column(DECIMAL(10, 4))
    
class Watchlist(Base):
    """User-defined monitoring thresholds for specific equities."""
    __tablename__ = 'watchlists'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), unique=True)
    target_price_above = Column(DECIMAL(15, 2), nullable=True)
    target_price_below = Column(DECIMAL(15, 2), nullable=True)
    sentiment_threshold = Column(DECIMAL(10, 4), nullable=True)
    is_active = Column(Integer, default=1) # 1 for active, 0 for paused
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Alert(Base):
    """Persistence record for triggered price or sentiment notifications."""
    __tablename__ = 'alerts'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    alert_type = Column(String(50)) # PRICE_ABOVE, PRICE_BELOW, SENTIMENT_SPIKE, etc.
    message = Column(String, nullable=False)
    trigger_value = Column(DECIMAL(15, 4))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


# Global engine singleton to prevent connection pool exhaustion
_engine = None

def get_engine():
    """Returns the global SQLAlchemy engine instance."""
    global _engine
    if _engine is None:
        DATABASE_URL = "postgresql+pg8000://postgres:postgres@127.0.0.1:5433/stock_intelligence"
        # Increased pool size and max overflow for institutional bulk loads
        _engine = create_engine(
            DATABASE_URL, 
            pool_size=10, 
            max_overflow=20,
            pool_recycle=3600
        )
    return _engine

def get_session():
    """Initializes and returns a new SQLAlchemy session from the shared engine."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
