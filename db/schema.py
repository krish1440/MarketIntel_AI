from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, BIGINT, DateTime, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Stock(Base):
    __tablename__ = 'stocks'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    exchange = Column(String(10), nullable=False)

class LiveQuote(Base):
    __tablename__ = 'live_quotes'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    price = Column(DECIMAL(15, 2), nullable=False)
    change_percent = Column(DECIMAL(10, 4))
    volume = Column(BIGINT)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class HistoricalPrice(Base):
    __tablename__ = 'historical_prices'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    date = Column(Date, nullable=False)
    open = Column(DECIMAL(15, 2))
    high = Column(DECIMAL(15, 2))
    low = Column(DECIMAL(15, 2))
    close = Column(DECIMAL(15, 2))
    volume = Column(BIGINT)

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    title = Column(String, nullable=False)
    summary = Column(String)
    url = Column(String, unique=True, nullable=False)
    published_at = Column(DateTime)
    sentiment_score = Column(DECIMAL(10, 4), nullable=True)

def get_engine():
    # Database credentials matching docker-compose.yml
    DATABASE_URL = "postgresql://admin:password@localhost:5432/stock_intelligence"
    return create_engine(DATABASE_URL)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
