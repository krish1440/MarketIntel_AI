"""
MarketIntel AI: High-Performance Neural Gateway
===============================================

This module serves as the primary RESTful interface for the MarketIntel AI ecosystem.
It acts as the central orchestrator, bridging the gap between high-frequency market
data, historical archives, and the underlying neural intelligence stack.

The API is built on FastAPI for asynchronous performance and follows a 
service-oriented architecture (SOA) pattern, specifically designed to handle
the high-latency requirements of deep learning model inference and RSS-based 
news aggregation.

Architecture Components:
------------------------
1. Discovery Engine: Paginated stock universe exploration with fuzzy search.
2. Intelligence Node: LSTM-based price forecasting and Transformers-based sentiment analysis.
3. Persistence Layer: Real-time mapping of SQLAlchemy models to JSON-serializable structures.
4. Sanitization: Recursive NaN-management to ensure browser-side rendering stability.

Author: MarketIntel AI Engineering Group
Version: 2.1.0 (Production)
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import json
import numpy as np
import feedparser
import urllib.parse
import datetime
from bs4 import BeautifulSoup

# Add parent directory to path for cross-module relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, NewsArticle, LiveQuote
from intelligence.prediction_service import PredictionService

# Global Application Instance
app = FastAPI(
    title="Stock Market Intelligence API",
    description="Advanced REST interface for MarketIntel AI Terminal",
    version="2.1.0"
)

# CORS Policy: Institutional Open-Access Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_nas(obj):
    """
    Recursively cleans and sanitizes data objects for JSON serialization.

    The primary purpose is to convert NumPy-specific NaN (Not a Number) values 
    into standard 0.0 floats. This is a critical stability feature for Next.js 
    hydration, as 'NaN' is not a valid JSON value and would cause frontend crashes.

    Args:
        obj (any): The input data structure (dict, list, or primitive).

    Returns:
        any: The sanitized, JSON-compliant version of the input object.
    """
    if isinstance(obj, dict):
        return {k: clean_nas(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nas(v) for v in obj]
    elif isinstance(obj, (float, np.float64, np.float32)) and np.isnan(obj):
        return 0.0
    return obj

# Initialize Singleton Prediction Service
predict_service = PredictionService()

@app.get("/api/stocks")
def list_stocks(
    page: int = Query(1, ge=1, description="The page number to retrieve"),
    limit: int = Query(50, ge=1, le=100, description="Number of records per page"),
    search: str = Query(None, description="Fuzzy search query for ticker or company name")
):
    """
    Retrieves a paginated list of stocks with real-time price summaries.

    This endpoint acts as the main discovery feed for the dashboard. It joins 
    static stock metadata with the latest 'LiveQuote' snapshots from the database.

    Args:
        page (int): Current pagination index.
        limit (int): Size of the data chunk per request.
        search (str, optional): Filters results by ticker symbol or full company name.

    Returns:
        dict: A sanitized object containing pagination metadata and stock records.
    """
    session = get_session()
    
    # Base query for the Stock repository
    query = session.query(Stock)
    
    # Apply fuzzy search filter across multiple metadata fields
    if search:
        query = query.filter(
            (Stock.ticker.ilike(f"%{search}%")) | 
            (Stock.name.ilike(f"%{search}%"))
        )
    
    total = query.count()
    stocks = query.offset((page - 1) * limit).limit(limit).all()
    
    results = []
    for s in stocks:
        # Fetch the most recent price snapshot for the NSE exchange
        latest = session.query(LiveQuote).filter_by(
            stock_id=s.id, exchange='NSE'
        ).order_by(LiveQuote.timestamp.desc()).first()
        
        results.append({
            "id": s.id,
            "ticker": s.ticker,
            "name": s.name,
            "price": float(latest.price) if latest else 0.0,
            "change": float(latest.change_percent) if latest and latest.change_percent else 0.0
        })
    
    session.close()
    return clean_nas({
        "total": total,
        "page": page,
        "limit": limit,
        "stocks": results
    })

@app.get("/api/model-status")
def get_model_status():
    """
    Returns the current operational health of the neural prediction models.

    Reads metadata checkpoints to provide the last training date, RMSE (Error)
    metrics, and currency status of the LSTM weights.

    Returns:
        dict: Metadata regarding the neural stack's training state.
    """
    path = 'models/checkpoints/metadata.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {"status": "Initializing", "rmse_currency": 0.0}

@app.get("/api/predict/{ticker}")
def predict_stock(ticker: str, exchange: str = "NSE"):
    """
    Executes a neural price forecast for a specific ticker.

    Calls the PredictionService to feed the latest 100 days of historical 
    OHLCV data into the LSTM model and return a forward-looking signal.

    Args:
        ticker (str): The stock ticker to analyze.
        exchange (str): The exchange context (default: NSE).

    Returns:
        dict: A neural signal containing forecast prices and confidence levels.
    """
    return clean_nas(predict_service.get_signal(ticker, exchange))

@app.get("/api/history/{ticker}")
def get_history(ticker: str, exchange: str = "NSE", days: int = 30):
    """
    Fetches the historical price array for charting and technical analysis.

    Args:
        ticker (str): Target stock ticker.
        exchange (str): Exchange source (NSE/BSE).
        days (int): Number of previous trading days to retrieve.

    Returns:
        list: A chronologically sorted array of date-price pairs.
    """
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return []
    
    history = session.query(HistoricalPrice).filter_by(
        stock_id=stock.id, 
        exchange=exchange
    ).order_by(HistoricalPrice.date.desc()).limit(days).all()
    
    session.close()
    return clean_nas([{"date": h.date.isoformat(), "close": float(h.close)} for h in reversed(history) if h.close is not None and not np.isnan(float(h.close))])

def fetch_and_save_news(session, ticker):
    """
    Internal logic to bridge real-time news RSS feeds with AI Sentiment analysis.

    This function performs a targeted search, handles deduplication based on 
    unique URLs, and runs the Transformers model for each new headline.

    Args:
        session: SQLAlchemy session instance.
        ticker (str): Target ticker for the news fetch.

    Returns:
        int: Total number of new articles successfully ingested and scored.
    """
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return 0
    
    query = f"{stock.ticker} share price news"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    count = 0
    try:
        feed = feedparser.parse(rss_url)
        # Unique URL mapping to prevent DB pollution
        existing_urls = {u[0] for u in session.query(NewsArticle.url).filter_by(stock_id=stock.id).all()}
        
        for entry in feed.entries[:10]:
            if entry.link not in existing_urls:
                summary_text = ""
                if hasattr(entry, 'summary'):
                    soup = BeautifulSoup(entry.summary, 'html.parser')
                    summary_text = soup.get_text()
                
                pub_date = datetime.datetime.now()
                if hasattr(entry, 'published'):
                    try:
                        pub_date = datetime.datetime(*entry.published_parsed[:6])
                    except: pass
                
                # Neural Sentiment Injection
                text_to_analyze = f"{entry.title}. {summary_text[:200]}"
                try:
                    from models.sentiment_model import get_sentiment_score
                    score = get_sentiment_score(text_to_analyze)
                except:
                    score = 0.0

                article = NewsArticle(
                    stock_id=stock.id,
                    title=entry.title,
                    summary=summary_text[:500],
                    url=entry.link,
                    published_at=pub_date,
                    sentiment_score=score
                )
                session.add(article)
                count += 1
        session.commit()
    except Exception as e:
        print(f"Error refreshing news for {ticker}: {e}")
        session.rollback()
    return count

@app.get("/api/news/{ticker}")
def get_news(ticker: str):
    """
    Retrieves the most recent news articles for a stock with AI sentiment data.

    Args:
        ticker (str): Target stock ticker.

    Returns:
        list: Array of news objects including AI-generated sentiment scores.
    """
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return []
    
    news = session.query(NewsArticle).filter_by(stock_id=stock.id).order_by(NewsArticle.published_at.desc()).limit(10).all()
    session.close()
    return [{
        "title": n.title,
        "url": n.url,
        "sentiment": float(n.sentiment_score) if n.sentiment_score else 0,
        "date": n.published_at.isoformat()
    } for n in news]

@app.post("/api/news/refresh/{ticker}")
def refresh_news(ticker: str):
    """
    Triggers an on-demand real-time news refresh for a specific ticker.

    This endpoint allows the dashboard to bypass background sync cycles
    when a user requests immediate data for a deep-dive analysis.

    Args:
        ticker (str): Target ticker.

    Returns:
        dict: Count of new articles discovered.
    """
    session = get_session()
    new_count = fetch_and_save_news(session, ticker)
    session.close()
    return {"new_articles": new_count}

if __name__ == "__main__":
    import uvicorn
    # Entry point for production-grade Uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000)
