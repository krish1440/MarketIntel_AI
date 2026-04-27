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
def list_stocks():
    session = get_session()
    stocks = session.query(Stock).all()
    # Filter for unique tickers
    unique_stocks = []
    seen = set()
    for s in stocks:
        if s.ticker not in seen:
            # Get latest price for the dashboard list
            latest = session.query(LiveQuote).filter_by(stock_id=s.id, exchange='NSE').order_by(LiveQuote.timestamp.desc()).first()
            unique_stocks.append({
                "id": s.id,
                "ticker": s.ticker,
                "name": s.name,
                "price": float(latest.price) if latest else 0.0,
                "change": float(latest.change_percent) if latest and latest.change_percent else 0.0
            })
            seen.add(s.ticker)
    session.close()
    return clean_nas(unique_stocks)

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
    return clean_nas([{"date": h.date.isoformat(), "close": float(h.close)} for h in reversed(history) if h.close is not None and not (isinstance(h.close, float) and np.isnan(h.close))])

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
