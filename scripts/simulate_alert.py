"""
MARKETINTEL AI: ALERT SIMULATOR
===============================
This script simulates a price update for a stock to verify that the 
Watchlist/Alert system triggers correctly without needing to fetch 
live data from yfinance.
"""

import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, LiveQuote, Watchlist
from ingestion.alert_manager import AlertManager

def simulate_alert():
    session = get_session()
    alert_mgr = AlertManager(session)
    
    try:
        # 1. Ensure a test stock exists
        stock = session.query(Stock).filter_by(ticker='RELIANCE').first()
        if not stock:
            print("RELIANCE not found. Please run discover_symbols.py.")
            return

        # 2. Ensure it has low thresholds for testing
        watchlist = session.query(Watchlist).filter_by(stock_id=stock.id).first()
        if not watchlist:
            watchlist = Watchlist(stock_id=stock.id, target_price_above=100.0, sentiment_threshold=0.5, is_active=1)
            session.add(watchlist)
        else:
            watchlist.target_price_above = 100.0
            watchlist.sentiment_threshold = 0.5
            watchlist.is_active = 1
        
        session.commit()
        print(f"Set test thresholds for {stock.ticker}")

        # 3. Simulate a high price (should trigger PRICE_ABOVE)
        test_price = 3000.0

        print(f"Simulating price update: {stock.ticker} @ {test_price}")
        
        # This mirrors what poll_prices.py does
        alert_mgr.check_price_alerts(stock.id, test_price, stock.ticker)
        
        # 4. Simulate a sentiment update
        test_sentiment = 0.95
        print(f"Simulating sentiment update: {stock.ticker} @ {test_sentiment}")
        
        # This mirrors what news_aggregator.py does
        alert_mgr.check_sentiment_alerts(stock.id, test_sentiment, stock.ticker)
        
        print("\nSUCCESS: Simulation complete. Run view_alerts.py to see the results.")

    except Exception as e:
        print(f"Error during simulation: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    simulate_alert()
