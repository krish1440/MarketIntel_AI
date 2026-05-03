"""
MarketIntel AI: Test Watchlist Seeder
=====================================

This utility seeds the database with a high-sensitivity 'Watchlist' entry 
for RELIANCE. It is used primarily by developers to verify that the 
asynchronous AlertManager triggers notifications successfully.
"""

import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, Watchlist

def setup_test():
    """
    Injects a test watchlist entry into the database.
    
    The thresholds are intentionally set exceptionally low/high to ensure 
    that the next polling cycle or news ingestion immediately fires an alert.
    """
    session = get_session()
    
    # Target RELIANCE for testing
    stock = session.query(Stock).filter_by(ticker='RELIANCE').first()
    
    if not stock:
        print("RELIANCE not found in DB. Please run discover_symbols.py first.")
        return

    # Check if already in watchlist
    existing = session.query(Watchlist).filter_by(stock_id=stock.id).first()
    if existing:
        session.delete(existing)
        session.commit()

    # Add TCS with very tight thresholds to trigger alerts easily for testing
    # Note: Use a stock that moves to see it in action
    test_watchlist = Watchlist(
        stock_id=stock.id,
        target_price_above=100.0, # Very low, should trigger immediately
        target_price_below=10000.0, # Very high, should trigger immediately
        sentiment_threshold=0.1, # Very low, most news will trigger this
        is_active=1
    )
    
    session.add(test_watchlist)
    session.commit()
    print(f"✅ Test Watchlist set up for {stock.ticker}.")
    print("Thresholds: Price > 100, Price < 10000, Sentiment > 0.1")
    print("Now run poll_prices.py or news_aggregator.py to see alerts in the console.")
    
    session.close()

if __name__ == "__main__":
    setup_test()
