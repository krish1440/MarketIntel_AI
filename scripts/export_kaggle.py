"""
MarketIntel AI: Legacy Kaggle Export Engine
===========================================
This module handles the full-scale export of the stock market database into 
Kaggle-compliant CSV formats. It supports both 'Long Format' (OHLCV) and 
'Wide Format' (Time-Series Matrix).

Note: This engine performs full re-exports. For incremental updates, see 'smart_export.py'.
"""
import sys
import os
import csv

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, HistoricalPrice, Stock

def export_to_kaggle_long(session, export_dir):
    """
    Exports full OHLCV data in Long Format (one row per date per stock).

    This function uses a memory-efficient batching strategy to process millions 
    of records without overloading the system RAM. It maps database IDs back 
    to tickers in real-time.

    Args:
        session (sqlalchemy.orm.Session): The active database session.
        export_dir (str): The destination directory for the generated CSV.

    Returns:
        None: The output is written directly to the filesystem.
    """
    filename = os.path.join(export_dir, "indian_stocks_all_history.csv")
    print(f"\n[INFO] Exporting LONG Format (OHLCV)...")
    
    print(f"\n[INFO] Loading stock metadata...")
    stocks = {s.id: s.ticker for s in session.query(Stock.id, Stock.ticker).all()}
    total_count = session.query(HistoricalPrice).count()
    
    batch_size = 100000
    processed = 0
    last_id = 0
    
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ticker', 'exchange', 'date', 'open', 'high', 'low', 'close', 'volume'])
        
        while True:
            batch = session.query(
                HistoricalPrice.id,
                HistoricalPrice.stock_id,
                HistoricalPrice.exchange,
                HistoricalPrice.date,
                HistoricalPrice.open,
                HistoricalPrice.high,
                HistoricalPrice.low,
                HistoricalPrice.close,
                HistoricalPrice.volume
            ).filter(HistoricalPrice.id > last_id)\
             .order_by(HistoricalPrice.id)\
             .limit(batch_size).all()
            
            if not batch:
                break
                
            for row in batch:
                ticker = stocks.get(row.stock_id, "UNKNOWN")
                writer.writerow([
                    ticker, row.exchange, row.date.isoformat(),
                    row.open, row.high, row.low, row.close, row.volume
                ])
                last_id = row.id
                
            processed += len(batch)
            print(f"  Progress: {processed}/{total_count} records ({(processed/total_count)*100:.1f}%)", end='\r', flush=True)
            
    print(f"\n[SUCCESS] LONG Format ready: {filename}")

def export_to_kaggle_wide(session, export_dir):
    """Exports Closing Prices in Wide Format Matrix (one row per stock, dates as columns)."""
    filename = os.path.join(export_dir, "indian_stocks_time_series_matrix.csv")
    print(f"\n[INFO] Exporting WIDE Matrix Format (Closing Prices)...")
    
    # Get all unique dates
    unique_dates = [d[0] for d in session.query(HistoricalPrice.date).distinct().order_by(HistoricalPrice.date.asc()).all()]
    date_headers = [d.isoformat() for d in unique_dates]
    
    # Get all unique (stock_id, exchange) pairs that actually have data
    stock_exchange_pairs = session.query(
        HistoricalPrice.stock_id, 
        HistoricalPrice.exchange
    ).distinct().all()
    
    total_rows = len(stock_exchange_pairs)
    
    # Map stock IDs to tickers for fast lookup
    stock_map = {s.id: s.ticker for s in session.query(Stock.id, Stock.ticker).all()}
    
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ticker', 'exchange'] + date_headers)
        
        for i, (s_id, exch) in enumerate(stock_exchange_pairs):
            ticker = stock_map.get(s_id, "UNKNOWN")
            
            # Get prices for THIS specific stock and THIS specific exchange
            prices = session.query(HistoricalPrice.date, HistoricalPrice.close)\
                            .filter_by(stock_id=s_id, exchange=exch).all()
            
            price_map = {p.date.isoformat(): float(p.close) if p.close is not None else "" for p in prices}
            
            row = [ticker, exch]
            for d in date_headers:
                row.append(price_map.get(d, ""))
                
            writer.writerow(row)
            if (i + 1) % 100 == 0 or (i + 1) == total_rows:
                print(f"  Progress: {i+1}/{total_rows} rows ({( (i+1)/total_rows )*100:.1f}%)", end='\r')
                
    print(f"\n[SUCCESS] WIDE Matrix ready: {filename}")

def main():
    session = get_session()
    export_dir = "data_exports"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
        
    # Run both exports
    export_to_kaggle_long(session, export_dir)
    export_to_kaggle_wide(session, export_dir)
    
    session.close()
    print("\n\n🌟 ALL EXPORTS COMPLETE! Your Kaggle Portfolio is ready.")

if __name__ == "__main__":
    main()
