from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import pandas as pd
from typing import List

# Add parent directory to path for db and model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, LiveQuote, HistoricalPrice, NewsArticle
from intelligence.prediction_service import PredictionService

app = FastAPI(title="Stock Market Intelligence API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

predict_service = PredictionService()

@app.get("/api/stocks")
def get_stocks():
    session = get_session()
    stocks = session.query(Stock).all()
    result = []
    for s in stocks:
        # Get latest price
        latest = session.query(LiveQuote).filter_by(stock_id=s.id).order_by(LiveQuote.timestamp.desc()).first()
        result.append({
            "id": s.id,
            "ticker": s.ticker,
            "name": s.name,
            "exchange": s.exchange,
            "price": float(latest.price) if latest else 0.0,
            "change": float(latest.change_percent) if latest and latest.change_percent else 0.0
        })
    session.close()
    return result

@app.get("/api/predict/{ticker}")
def predict_stock(ticker: str):
    try:
        return predict_service.get_signal(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/news/{ticker}")
def get_stock_news(ticker: str):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock:
        session.close()
        raise HTTPException(status_code=404, detail="Stock not found")
        
    news = session.query(NewsArticle).filter_by(stock_id=stock.id).order_by(NewsArticle.published_at.desc()).limit(10).all()
    result = [{
        "title": n.title,
        "summary": n.summary,
        "url": n.url,
        "published_at": n.published_at,
        "sentiment": float(n.sentiment_score) if n.sentiment_score is not None else 0.0
    } for n in news]
    session.close()
    return result

@app.get("/api/history/{ticker}")
def get_history(ticker: str):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock:
        session.close()
        raise HTTPException(status_code=404, detail="Stock not found")
        
    history = session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.desc()).limit(30).all()
    result = [{
        "date": h.date,
        "open": float(h.open),
        "high": float(h.high),
        "low": float(h.low),
        "close": float(h.close),
        "volume": int(h.volume)
    } for h in reversed(history)]
    session.close()
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
