
import sys
import os
import pandas as pd
from sqlalchemy import create_engine

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, NewsArticle, HistoricalFundamentals, HistoricalPrice

def sample_data():
    session = get_session()
    
    print("=== FUNDAMENTAL DATA IN STOCKS TABLE ===")
    stocks = session.query(Stock).filter(Stock.pe_ratio != None).limit(5).all()
    if not stocks:
        print("No fundamental data found in stocks table.")
    for s in stocks:
        print(f"Ticker: {s.ticker} | PE: {s.pe_ratio} | EPS: {s.eps} | Sector: {s.sector}")
        
    print("\n=== HISTORICAL FUNDAMENTALS (Time Series) ===")
    h_funds = session.query(HistoricalFundamentals).limit(5).all()
    if not h_funds:
        print("No historical fundamental snapshots found yet.")
    for h in h_funds:
        print(f"Stock ID: {h.stock_id} | Date: {h.date} | PE: {h.pe_ratio} | EPS: {h.eps}")
        
    print("\n=== NEWS SENTIMENT STATUS ===")
    total_news = session.query(NewsArticle).count()
    news_with_sentiment = session.query(NewsArticle).filter(NewsArticle.sentiment_score != None).count()
    print(f"Total News: {total_news} | News with Sentiment: {news_with_sentiment}")
    
    if news_with_sentiment > 0:
        samples = session.query(NewsArticle).filter(NewsArticle.sentiment_score != None).limit(3).all()
        for n in samples:
            # Use ascii representation to avoid encoding errors in logs
            title_clean = n.title.encode('ascii', 'ignore').decode('ascii')
            print(f"Title: {title_clean[:60]}... | Score: {n.sentiment_score}")

    session.close()

if __name__ == "__main__":
    try:
        sample_data()
    except Exception as e:
        print(f"Error sampling data: {e}")
