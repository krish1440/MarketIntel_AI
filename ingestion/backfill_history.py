import yfinance as yf
import datetime
import sys
import os
import pandas as pd

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice

def get_yahoo_ticker(symbol, exchange):
    if exchange == 'NSE':
        return f"{symbol}.NS"
    elif exchange == 'BSE':
        # BSE symbols on Yahoo can be scrip codes or symbols
        # For simplicity, if it's numeric, it's likely a BSE scrip code
        if symbol.isdigit():
            return f"{symbol}.BO"
        return f"{symbol}.BO"
    return symbol

def backfill_stock(session, stock, period="2y"):
    yahoo_symbol = get_yahoo_ticker(stock.ticker, stock.exchange)
    print(f"Fetching history for {stock.ticker} ({yahoo_symbol})...")
    
    try:
        ticker = yf.Ticker(yahoo_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            print(f"  No data found for {yahoo_symbol}")
            return

        count = 0
        for date, row in df.iterrows():
            # Check if record already exists
            existing = session.query(HistoricalPrice).filter_by(
                stock_id=stock.id, 
                date=date.date()
            ).first()
            
            if not existing:
                hist = HistoricalPrice(
                    stock_id=stock.id,
                    date=date.date(),
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=int(row['Volume'])
                )
                session.add(hist)
                count += 1
        
        session.commit()
        print(f"  Saved {count} new records.")
        
    except Exception as e:
        print(f"  Error backfilling {stock.ticker}: {e}")
        session.rollback()

def main():
    session = get_session()
    stocks = session.query(Stock).all()
    
    if not stocks:
        print("No stocks found in database.")
        return

    for stock in stocks:
        backfill_stock(session, stock)
    
    session.close()
    print("Backfill complete.")

if __name__ == "__main__":
    main()
