import yfinance as yf
import time
import sys
import os
from datetime import datetime

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, LiveQuote

def poll_prices():
    session = get_session()
    stocks = session.query(Stock).all()
    
    print(f"Starting dual-exchange polling for {len(stocks)} companies...")
    
    while True:
        try:
            for stock in stocks:
                # Poll NSE
                if stock.nse_symbol:
                    print(f"Polling {stock.ticker} (NSE)... ", end="", flush=True)
                    ticker_nse = yf.Ticker(stock.nse_symbol)
                    info = ticker_nse.fast_info
                    price = info['lastPrice']
                    prev_close = info['previousClose']
                    change = ((price / prev_close) - 1) * 100 if prev_close else 0
                    
                    quote_nse = LiveQuote(
                        stock_id=stock.id,
                        exchange='NSE',
                        price=price,
                        change_percent=change
                    )
                    session.add(quote_nse)
                    print(f"NSE Price: {price:.2f} ({change:+.2f}%)")

                # Poll BSE
                if stock.bse_symbol:
                    print(f"Polling {stock.ticker} (BSE)... ", end="", flush=True)
                    ticker_bse = yf.Ticker(stock.bse_symbol)
                    info_b = ticker_bse.fast_info
                    price_b = info_b['lastPrice']
                    prev_close_b = info_b['previousClose']
                    change_b = ((price_b / prev_close_b) - 1) * 100 if prev_close_b else 0
                    
                    quote_bse = LiveQuote(
                        stock_id=stock.id,
                        exchange='BSE',
                        price=price_b,
                        change_percent=change_b
                    )
                    session.add(quote_bse)
                    print(f"BSE Price: {price_b:.2f} ({change_b:+.2f}%)")

            session.commit()
            time.sleep(60) # Poll every minute
            
        except Exception as e:
            print(f"\nError in polling loop: {e}")
            session.rollback()
            time.sleep(10)

if __name__ == "__main__":
    poll_prices()
