"""
MarketIntel AI: Smart Delta Sync Engine
=======================================
Implements high-speed, incremental data ingestion for the stock universe. 
Unlike standard backfills, this engine identifies 'data holes'—the gap 
between the last recorded trade and today—and patches them differentially.

Key Features:
- Differential 'Catch-up' logic (saves bandwidth/time).
- Batch-Processing with Cooling Periods (respects YFinance Rate Limits).
- Automatic database connection management.
"""
import yfinance as yf
import datetime
import time
import sys
import os
import pandas as pd

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def update_exchange(session, stocks, exchange_type):
    symbol_attr = 'nse_symbol' if exchange_type == 'NSE' else 'bse_symbol'
    stocks_to_update = [s for s in stocks if getattr(s, symbol_attr)]
    
    if not stocks_to_update:
        return

    print(f"[DELTA] Checking for missing {exchange_type} data...")
    
    # Process in smaller batches of 20 to avoid rate limits
    for chunk in chunk_list(stocks_to_update, 20):
        tickers = [getattr(s, symbol_attr) for s in chunk]
        try:
            print(f"  [SYNC] Fetching chunk of {len(tickers)} tickers...")
            # We fetch 5 days to cover weekends
            data = yf.download(tickers, period="5d", interval="1d", progress=False, group_by='ticker')
            
            if data.empty: 
                time.sleep(2) # Cooling period on empty data
                continue
            
            # Map of ticker -> stock object for fast lookup
            ticker_map = {getattr(s, symbol_attr): s for s in chunk}
            
            for ticker_symbol in tickers:
                # Handle single vs multi-ticker dataframe structure from yfinance
                ticker_df = data[ticker_symbol] if len(tickers) > 1 else data
                
                if ticker_df.empty or 'Close' not in ticker_df: continue
                
                stock = ticker_map[ticker_symbol]
                
                # Get the latest date we have for this stock
                latest_record = session.query(HistoricalPrice.date).filter_by(
                    stock_id=stock.id, exchange=exchange_type
                ).order_by(HistoricalPrice.date.desc()).first()
                
                latest_date = latest_record[0] if latest_record else datetime.date(2000,1,1)
                
                s_close = ticker_df['Close'].dropna()
                new_records = []
                
                for date, price in s_close.items():
                    d = date.date()
                    if d > latest_date:
                        hist = HistoricalPrice(
                            stock_id=stock.id, exchange=exchange_type,
                            date=d,
                            open=float(ticker_df['Open'][date]),
                            high=float(ticker_df['High'][date]),
                            low=float(ticker_df['Low'][date]),
                            close=float(price),
                            volume=int(ticker_df['Volume'][date])
                        )
                        new_records.append(hist)
                
                if new_records:
                    session.add_all(new_records)
                    print(f"    [+] {stock.ticker}: {len(new_records)} new days.")
            
            session.commit()
            time.sleep(1.5) # Mandatory cooling period to avoid YF rate limits
            
        except Exception as e:
            print(f"  [!] Batch Error: {e}")
            session.rollback()
            time.sleep(5) # Longer cooling period on error

def main():
    session = get_session()
    stocks = session.query(Stock).all()
    
    start_time = time.time()
    update_exchange(session, stocks, 'NSE')
    update_exchange(session, stocks, 'BSE')
    
    session.close()
    print(f"[SUCCESS] Delta update complete in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
