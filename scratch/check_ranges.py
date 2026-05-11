
import sys
import os
from sqlalchemy import func

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, HistoricalPrice, HistoricalFundamentals

def check_date_ranges():
    session = get_session()
    
    print("=== HISTORICAL PRICE RANGE ===")
    price_stats = session.query(
        func.min(HistoricalPrice.date),
        func.max(HistoricalPrice.date),
        func.count(HistoricalPrice.id)
    ).one()
    print(f"Min Date: {price_stats[0]}")
    print(f"Max Date: {price_stats[1]}")
    print(f"Total Rows: {price_stats[2]}")
    
    print("\n=== HISTORICAL FUNDAMENTALS RANGE ===")
    fund_stats = session.query(
        func.min(HistoricalFundamentals.date),
        func.max(HistoricalFundamentals.date),
        func.count(HistoricalFundamentals.id)
    ).one()
    print(f"Min Date: {fund_stats[0]}")
    print(f"Max Date: {fund_stats[1]}")
    print(f"Total Rows: {fund_stats[2]}")

    session.close()

if __name__ == "__main__":
    try:
        check_date_ranges()
    except Exception as e:
        print(f"Error checking ranges: {e}")
