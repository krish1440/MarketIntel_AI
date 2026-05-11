
import sys
import os
from sqlalchemy import create_engine

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Watchlist, Alert

def sample_user_data():
    session = get_session()
    
    print("=== WATCHLIST SAMPLES ===")
    watch = session.query(Watchlist).limit(5).all()
    if not watch:
        print("Watchlist is currently empty.")
    for w in watch:
        print(f"Stock ID: {w.stock_id} | Target Above: {w.target_price_above} | Below: {w.target_price_below}")
        
    print("\n=== ALERT SAMPLES ===")
    alerts = session.query(Alert).limit(5).all()
    if not alerts:
        print("No alerts have been triggered yet.")
    for a in alerts:
        print(f"Type: {a.alert_type} | Message: {a.message} | Time: {a.timestamp}")

    session.close()

if __name__ == "__main__":
    try:
        sample_user_data()
    except Exception as e:
        print(f"Error sampling data: {e}")
