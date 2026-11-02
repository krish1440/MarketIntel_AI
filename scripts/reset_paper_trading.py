import sys
import sqlite3
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings

def reset_paper_trading():
    db_path = settings.BASE_DIR / "data" / "paper_trading" / "paper_ledger.db"
    if not db_path.exists():
        print(f"Database {db_path} does not exist yet.")
        return

    print(f"Resetting paper trading ledger at {db_path}...")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Clear all positions, trades, orders
        cursor.execute("DELETE FROM active_positions")
        cursor.execute("DELETE FROM trade_history")
        cursor.execute("DELETE FROM orders")
        
        # Reset portfolio state to fresh 10,00,000 INR
        cursor.execute("DELETE FROM portfolio_state")
        cursor.execute("INSERT INTO portfolio_state (key, value) VALUES ('cash', '1000000.0')")
        cursor.execute("INSERT INTO portfolio_state (key, value) VALUES ('peak_portfolio_value', '1000000.0')")
        cursor.execute("INSERT INTO portfolio_state (key, value) VALUES ('day_start_value', '1000000.0')")
        
        conn.commit()

    print("SUCCESS: Paper trading database reset to fresh state:")
    print("  - Active Positions: 0")
    print("  - Trade History: 0")
    print("  - Orders: 0")
    print("  - Available Cash: Rs. 10,00,000.00")
    print("  - Total Portfolio Equity: Rs. 10,00,000.00")

if __name__ == "__main__":
    reset_paper_trading()
