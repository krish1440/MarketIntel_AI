
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, HistoricalFundamentals, NewsArticle

def check_system_status():
    session = get_session()
    print("="*60)
    print(f"MARKETINTEL AI: GLOBAL DATA AUDIT ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("="*60)
    
    # 1. Stocks
    stock_count = session.query(Stock).count()
    print(f"[STOCKS] Universe Size: {stock_count} companies")
    
    # 2. Prices
    price_stats = session.query(
        func.count(HistoricalPrice.id),
        func.min(HistoricalPrice.date),
        func.max(HistoricalPrice.date)
    ).one()
    print(f"[PRICES] Total Records: {price_stats[0]:,}")
    print(f"[PRICES] Temporal Range: {price_stats[1]} to {price_stats[2]}")
    
    # 3. Fundamentals
    fund_stats = session.query(
        func.count(HistoricalFundamentals.id),
        func.min(HistoricalFundamentals.date),
        func.max(HistoricalFundamentals.date)
    ).one()
    print(f"[FUNDAMENTALS] Total Records: {fund_stats[0]:,}")
    print(f"[FUNDAMENTALS] Temporal Range: {fund_stats[1]} to {fund_stats[2]}")
    
    # Check for duplicates (should be 0)
    dup_count = session.query(HistoricalFundamentals.stock_id, HistoricalFundamentals.date)\
                       .group_by(HistoricalFundamentals.stock_id, HistoricalFundamentals.date)\
                       .having(func.count(HistoricalFundamentals.id) > 1).count()
    print(f"[INTEGRITY] Duplicate Fundamentals: {dup_count} (Goal: 0)")
    
    # 4. Sentiment
    news_count = session.query(NewsArticle).count()
    sentiment_avg = session.query(func.avg(NewsArticle.sentiment_score)).scalar() or 0
    print(f"[SENTIMENT] Total News: {news_count:,} articles")
    print(f"[SENTIMENT] Market Bias: {float(sentiment_avg):.2f} (-1 to 1)")
    
    # 5. Model Checkpoint
    checkpoint_path = 'models/checkpoints/metadata.json'
    if os.path.exists(checkpoint_path):
        import json
        with open(checkpoint_path, 'r') as f:
            meta = json.load(f)
            print(f"[MODELS] Status: {meta.get('status', 'Unknown')}")
            print(f"[MODELS] Last Trained: {meta.get('last_train', 'N/A')}")
            print(f"[MODELS] RMSE Accuracy: ±₹{meta.get('rmse_currency', 0):.2f}")
    
    print("="*60)
    session.close()

if __name__ == "__main__":
    check_system_status()
