"""
MarketIntel AI: High-Performance Neural Gateway
===============================================
Central REST API for the MarketIntel ecosystem. Orchestrates data flow 
between PostgreSQL, the LSTM Prediction Engine, and the Sentiment Expert.
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import json
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, NewsArticle, LiveQuote
from intelligence.prediction_service import PredictionService

app = FastAPI(title="Stock Market Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_nas(obj):
    if isinstance(obj, dict):
        return {k: clean_nas(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nas(v) for v in obj]
    elif isinstance(obj, (float, np.float64, np.float32)) and np.isnan(obj):
        return 0.0
    return obj

predict_service = PredictionService()

@app.get("/api/stocks")
def list_stocks(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None)
):
    session = get_session()
    
    # Base query
    query = session.query(Stock)
    
    # Filter by search
    if search:
        query = query.filter(
            (Stock.ticker.ilike(f"%{search}%")) | 
            (Stock.name.ilike(f"%{search}%"))
        )
    
    # Get total count for pagination
    total = query.count()
    
    # Pagination
    stocks = query.offset((page - 1) * limit).limit(limit).all()
    
    # Filter for unique tickers and attach prices
    results = []
    for s in stocks:
        # Get latest NSE price
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
    path = 'models/checkpoints/metadata.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {"status": "Initializing", "rmse_currency": 0.0}

@app.get("/api/predict/{ticker}")
def predict_stock(ticker: str, exchange: str = "NSE"):
    return clean_nas(predict_service.get_signal(ticker, exchange))

@app.get("/api/history/{ticker}")
def get_history(ticker: str, exchange: str = "NSE", days: int = 30):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return []
    
    history = session.query(HistoricalPrice).filter_by(
        stock_id=stock.id, 
        exchange=exchange
    ).order_by(HistoricalPrice.date.desc()).limit(days).all()
    
    session.close()
    return clean_nas([{"date": h.date.isoformat(), "close": float(h.close)} for h in reversed(history) if h.close is not None and not np.isnan(float(h.close))])

import feedparser
import urllib.parse
import datetime
from bs4 import BeautifulSoup

def fetch_and_save_news(session, ticker):
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return 0
    
    query = f"{stock.ticker} share price news"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    count = 0
    try:
        feed = feedparser.parse(rss_url)
        # Get existing URLs to avoid duplicates
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
                
                # Calculate AI Sentiment
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
    session = get_session()
    new_count = fetch_and_save_news(session, ticker)
    session.close()
    return {"new_articles": new_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
