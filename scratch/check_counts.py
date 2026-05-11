
import sys
import os
from sqlalchemy import func

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, HistoricalFundamentals

def check_counts():
    session = get_session()
    
    stock_count = session.query(Stock).count()
    price_count = session.query(HistoricalPrice).count()
    fund_count = session.query(HistoricalFundamentals).count()
    
    print(f"Total Stocks: {stock_count}")
    print(f"Total Prices: {price_count}")
    print(f"Total Fundamental Rows: {fund_count}")
    
    # Check a specific stock like RELIANCE
    reliance = session.query(Stock).filter(Stock.ticker == 'RELIANCE').first()
    if reliance:
        r_prices = session.query(func.min(HistoricalPrice.date), func.max(HistoricalPrice.date), func.count(HistoricalPrice.id)).filter_by(stock_id=reliance.id).one()
        r_funds = session.query(func.min(HistoricalFundamentals.date), func.max(HistoricalFundamentals.date), func.count(HistoricalFundamentals.id)).filter_by(stock_id=reliance.id).one()
        print(f"\n--- RELIANCE Stats ---")
        print(f"Prices: {r_prices[0]} to {r_prices[1]} ({r_prices[2]} rows)")
        print(f"Fundamentals: {r_funds[0]} to {r_funds[1]} ({r_funds[2]} rows)")

    session.close()

if __name__ == "__main__":
    try:
        check_counts()
    except Exception as e:
        print(f"Error checking counts: {e}")
