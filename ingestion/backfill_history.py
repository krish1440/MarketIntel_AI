import yfinance as yf
import datetime
import time
import sys
import os
import pandas as pd

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice

def backfill_stock_exchange(session, stock, symbol, exchange, period="5y"):
    if not symbol: return
    
    # Get all existing dates for this stock/exchange to avoid duplicates
    existing_dates = {
        res[0] for res in session.query(HistoricalPrice.date).filter_by(
            stock_id=stock.id, 
            exchange=exchange
        ).all()
    }
    
    if len(existing_dates) > 1000: # Assuming ~5 years is 1250 days
        print(f"Skipping {stock.ticker} ({exchange}) - Already backfilled.")
        return

    print(f"Fetching {exchange} history for {stock.ticker} ({symbol})...", flush=True)
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            print(f"  No data found for {symbol}")
            return
            
        df = df.dropna(subset=['Close'])

        new_records = []
        for date, row in df.iterrows():
            d = date.date()
            if d not in existing_dates:
                hist = HistoricalPrice(
                    stock_id=stock.id,
                    exchange=exchange,
                    date=d,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=int(row['Volume'])
                )
                new_records.append(hist)
        
        if new_records:
            session.add_all(new_records)
            session.commit()
            print(f"  Saved {len(new_records)} new records for {stock.ticker}.")
        else:
            print(f"  No new records to save for {stock.ticker}.")
        
    except Exception as e:
        print(f"  Error backfilling {stock.ticker} ({exchange}): {e}")
        session.rollback()

def main():
    session = get_session()
    stocks = session.query(Stock).all()
    
    # Filter stocks that actually need backfilling (NSE)
    nse_stocks_to_fix = []
    for stock in stocks:
        if stock.nse_symbol:
            count = session.query(HistoricalPrice).filter_by(stock_id=stock.id, exchange='NSE').count()
            if count < 100:
                nse_stocks_to_fix.append(stock)
    
    print(f"Found {len(nse_stocks_to_fix)} NSE stocks needing backfill.", flush=True)
    
    # Chunking helper
    def chunk_list(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    # Batch Backfill NSE
    for chunk in chunk_list(nse_stocks_to_fix, 50):
        tickers = [s.nse_symbol for s in chunk]
        print(f"Batch fetching history for {len(tickers)} NSE stocks...", flush=True)
        try:
            # Fetch 5 years of daily data for the whole chunk
            data = yf.download(tickers, period="5y", interval="1d", progress=False)
            if data.empty: continue
            
            close_data = data['Close']
            open_data = data['Open']
            high_data = data['High']
            low_data = data['Low']
            vol_data = data['Volume']
            
            for stock in chunk:
                if stock.nse_symbol in close_data:
                    # Get series and drop NaNs
                    s_close = close_data[stock.nse_symbol].dropna()
                    if s_close.empty: continue
                    
                    # Get existing dates to avoid duplicates
                    existing_dates = {
                        res[0] for res in session.query(HistoricalPrice.date).filter_by(
                            stock_id=stock.id, exchange='NSE'
                        ).all()
                    }
                    
                    new_records = []
                    for date, price in s_close.items():
                        d = date.date()
                        if d in existing_dates: continue
                        
                        hist = HistoricalPrice(
                            stock_id=stock.id, exchange='NSE',
                            date=d,
                            open=float(open_data[stock.nse_symbol][date]),
                            high=float(high_data[stock.nse_symbol][date]),
                            low=float(low_data[stock.nse_symbol][date]),
                            close=float(price),
                            volume=int(vol_data[stock.nse_symbol][date])
                        )
                        new_records.append(hist)
                    
                    if new_records:
                        session.add_all(new_records)
                        print(f"  Added {len(new_records)} records for {stock.ticker}", flush=True)
            
            session.commit()
            time.sleep(2) # Grace period between batches
            
        except Exception as e:
            print(f"Error in batch: {e}", flush=True)
            session.rollback()

    # --- Batch Backfill BSE ---
    bse_stocks_to_fix = []
    for stock in stocks:
        if stock.bse_symbol:
            count = session.query(HistoricalPrice).filter_by(stock_id=stock.id, exchange='BSE').count()
            if count < 100:
                bse_stocks_to_fix.append(stock)
    
    print(f"Found {len(bse_stocks_to_fix)} BSE stocks needing backfill.", flush=True)
    
    for chunk in chunk_list(bse_stocks_to_fix, 50):
        tickers = [s.bse_symbol for s in chunk]
        print(f"Batch fetching history for {len(tickers)} BSE stocks...", flush=True)
        try:
            data = yf.download(tickers, period="5y", interval="1d", progress=False)
            if data.empty: continue
            
            close_data = data['Close']
            open_data = data['Open']
            high_data = data['High']
            low_data = data['Low']
            vol_data = data['Volume']
            
            for stock in chunk:
                if stock.bse_symbol in close_data:
                    s_close = close_data[stock.bse_symbol].dropna()
                    if s_close.empty: continue
                    
                    # Get existing dates to avoid duplicates
                    existing_dates = {
                        res[0] for res in session.query(HistoricalPrice.date).filter_by(
                            stock_id=stock.id, exchange='BSE'
                        ).all()
                    }
                    
                    new_records = []
                    for date, price in s_close.items():
                        d = date.date()
                        if d in existing_dates: continue
                        
                        hist = HistoricalPrice(
                            stock_id=stock.id, exchange='BSE',
                            date=d,
                            open=float(open_data[stock.bse_symbol][date]),
                            high=float(high_data[stock.bse_symbol][date]),
                            low=float(low_data[stock.bse_symbol][date]),
                            close=float(price),
                            volume=int(vol_data[stock.bse_symbol][date])
                        )
                        new_records.append(hist)
                    
                    if new_records:
                        session.add_all(new_records)
                        print(f"  Added {len(new_records)} records for {stock.ticker} (BSE)", flush=True)
            
            session.commit()
            time.sleep(2)
            
        except Exception as e:
            print(f"Error in BSE batch: {e}", flush=True)
            session.rollback()

    session.close()
    print("Market backfill process complete.", flush=True)

if __name__ == "__main__":
    main()
