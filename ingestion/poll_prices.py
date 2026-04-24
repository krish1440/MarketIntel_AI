import time
import datetime
import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, LiveQuote

try:
    from nsepython import nse_quote_ltp
    NSE_AVAILABLE = True
except ImportError:
    print("Warning: nsepython not installed. Using mock for NSE.")
    NSE_AVAILABLE = False

try:
    from bsedata.bse import BSE
    BSE_OBJ = BSE()
    BSE_AVAILABLE = True
except ImportError:
    print("Warning: bsedata not installed. Using mock for BSE.")
    BSE_AVAILABLE = False

def fetch_nse_price(symbol):
    if NSE_AVAILABLE:
        try:
            return nse_quote_ltp(symbol)
        except Exception as e:
            print(f"Error fetching NSE {symbol}: {e}")
            return None
    else:
        # Mock for demo
        import random
        return 2500.0 + random.uniform(-10, 10)

def fetch_bse_price(symbol):
    if BSE_AVAILABLE:
        try:
            # bsedata uses security codes for some lookups, or scrip ids
            q = BSE_OBJ.getQuote(symbol)
            return float(q['currentValue'])
        except Exception as e:
            print(f"Error fetching BSE {symbol}: {e}")
            return None
    else:
        # Mock for demo
        import random
        return 2500.0 + random.uniform(-10, 10)

def main():
    session = get_session()
    
    # Get stocks to poll
    stocks = session.query(Stock).all()
    if not stocks:
        print("No stocks found in database. Please run init.sql seed data.")
        return

    print(f"Starting live polling for {len(stocks)} stocks...")
    
    try:
        while True:
            for stock in stocks:
                print(f"Polling {stock.ticker} on {stock.exchange}...")
                
                price = None
                if stock.exchange == 'NSE':
                    price = fetch_nse_price(stock.ticker)
                elif stock.exchange == 'BSE':
                    price = fetch_bse_price(stock.ticker)
                
                if price:
                    quote = LiveQuote(
                        stock_id=stock.id,
                        price=price,
                        timestamp=datetime.datetime.utcnow()
                    )
                    session.add(quote)
                    print(f"  Saved: {price}")
                
            session.commit()
            print(f"Cycle complete at {datetime.datetime.now()}. Sleeping for 60s...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("Polling stopped by user.")
    finally:
        session.close()

if __name__ == "__main__":
    main()
