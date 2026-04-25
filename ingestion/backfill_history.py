import yfinance as yf
import datetime
import sys
import os
import pandas as pd

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice

def backfill_stock_exchange(session, stock, symbol, exchange, period="2y"):
    if not symbol: return
    print(f"Fetching {exchange} history for {stock.ticker} ({symbol})...")
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            print(f"  No data found for {symbol}")
            return

        count = 0
        for date, row in df.iterrows():
            existing = session.query(HistoricalPrice).filter_by(
                stock_id=stock.id, 
                exchange=exchange,
                date=date.date()
            ).first()
            
            if not existing:
                hist = HistoricalPrice(
                    stock_id=stock.id,
                    exchange=exchange,
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
        print(f"  Error backfilling {stock.ticker} ({exchange}): {e}")
        session.rollback()

def main():
    session = get_session()
    stocks = session.query(Stock).all()
    
    for stock in stocks:
        # Backfill NSE
        backfill_stock_exchange(session, stock, stock.nse_symbol, "NSE", period="5y")
        # Backfill BSE
        backfill_stock_exchange(session, stock, stock.bse_symbol, "BSE", period="5y")
    
    session.close()
    print("Dual backfill complete.")

if __name__ == "__main__":
    main()
