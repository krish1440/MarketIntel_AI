
import sys
import os
from sqlalchemy import func

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, HistoricalFundamentals, Stock

def find_longest_history():
    session = get_session()
    
    # Get top 5 stocks by row count in HistoricalFundamentals
    top_stocks = session.query(
        HistoricalFundamentals.stock_id, 
        func.count(HistoricalFundamentals.id).label('count'),
        func.min(HistoricalFundamentals.date).label('min_date'),
        func.max(HistoricalFundamentals.date).label('max_date')
    ).group_by(HistoricalFundamentals.stock_id).order_by(func.count(HistoricalFundamentals.id).desc()).limit(5).all()
    
    for s_id, count, min_d, max_d in top_stocks:
        stock = session.query(Stock).filter_by(id=s_id).first()
        print(f"Stock: {stock.ticker if stock else s_id} | Count: {count} | Range: {min_d} to {max_d}")

    session.close()

if __name__ == "__main__":
    try:
        find_longest_history()
    except Exception as e:
        print(f"Error: {e}")
