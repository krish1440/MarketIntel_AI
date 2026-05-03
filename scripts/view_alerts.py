"""
MarketIntel AI: Alert Viewer Terminal
=====================================

A read-only command-line utility that fetches and displays the 10 most 
recent alerts triggered by the intelligence system. Useful for server 
monitoring via SSH.
"""

import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Alert, Stock

def view_alerts():
    """
    Connects to the database and prints the top 10 most recent alerts in 
    descending chronological order.
    """
    session = get_session()
    try:
        alerts = session.query(Alert).join(Stock).order_by(Alert.timestamp.desc()).limit(10).all()
        
        print("\n" + "="*50)
        print("--- LATEST MARKET ALERTS ---")
        print("="*50)
        
        if not alerts:
            print("No alerts triggered yet. (Try running ingestion/poll_prices.py)")
        else:
            for alert in alerts:
                time_str = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{time_str}] {alert.message}")

        
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"Error reading alerts: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    view_alerts()
