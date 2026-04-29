import sys
import os
import csv
import pandas as pd
import datetime

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, HistoricalPrice, Stock

def smart_export_long(session, export_dir):
    """Additive export for Long Format: Appends only new rows since the last date in the CSV."""
    filename = os.path.join(export_dir, "indian_stocks_all_history.csv")
    
    last_date = None
    if os.path.exists(filename):
        try:
            # Read only the last few rows to get the latest date
            df_last = pd.read_csv(filename, usecols=['date']).tail(1)
            if not df_last.empty:
                last_date = datetime.datetime.strptime(df_last['date'].iloc[0], "%Y-%m-%d").date()
                print(f"[SMART] Long Format: Found existing data up to {last_date}. Appending new records...")
        except Exception as e:
            print(f"[WARN] Could not read existing Long Format CSV: {e}. Rebuilding...")

    if last_date is None:
        # Full Export Logic (Standard)
        print("[INFO] Long Format: Starting fresh full export...")
        stocks = {s.id: s.ticker for s in session.query(Stock.id, Stock.ticker).all()}
        batch_size = 100000
        last_id = 0
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ticker', 'exchange', 'date', 'open', 'high', 'low', 'close', 'volume'])
            while True:
                batch = session.query(HistoricalPrice).filter(HistoricalPrice.id > last_id).order_by(HistoricalPrice.id).limit(batch_size).all()
                if not batch: break
                for row in batch:
                    writer.writerow([stocks.get(row.stock_id, "UNK"), row.exchange, row.date.isoformat(), row.open, row.high, row.low, row.close, row.volume])
                    last_id = row.id
    else:
        # Smart Append Logic
        stocks = {s.id: s.ticker for s in session.query(Stock.id, Stock.ticker).all()}
        new_records = session.query(HistoricalPrice).filter(HistoricalPrice.date > last_date).all()
        if not new_records:
            print("[INFO] Long Format: No new records to append.")
            return

        with open(filename, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in new_records:
                writer.writerow([stocks.get(row.stock_id, "UNK"), row.exchange, row.date.isoformat(), row.open, row.high, row.low, row.close, row.volume])
        print(f"[SUCCESS] Long Format: Appended {len(new_records)} new records.")

def smart_export_wide(session, export_dir):
    """Additive export for Wide Format: Adds new date columns to the existing matrix."""
    filename = os.path.join(export_dir, "indian_stocks_time_series_matrix.csv")
    
    if not os.path.exists(filename):
        print("[INFO] Wide Format: No existing matrix found. Rebuilding full matrix...")
        # Fallback to full logic (simplified)
        from scripts.export_kaggle import export_to_kaggle_wide
        export_to_kaggle_wide(session, export_dir)
        return

    print("[SMART] Wide Format: Loading existing matrix to add new columns...")
    df_matrix = pd.read_csv(filename)
    existing_dates = set(df_matrix.columns[2:]) # Skip ticker, exchange
    
    # Find all unique dates in DB
    db_dates = [d[0] for d in session.query(HistoricalPrice.date).distinct().order_by(HistoricalPrice.date.asc()).all()]
    new_dates = [d for d in db_dates if d.isoformat() not in existing_dates]
    
    if not new_dates:
        print("[INFO] Wide Format: All date columns are already present.")
        return

    print(f"[INFO] Wide Format: Adding {len(new_dates)} new date columns...")
    
    # Process each new date
    for d in new_dates:
        d_str = d.isoformat()
        # Fetch prices for this specific date for all stocks
        prices = session.query(Stock.ticker, HistoricalPrice.exchange, HistoricalPrice.close)\
                        .join(HistoricalPrice)\
                        .filter(HistoricalPrice.date == d).all()
        
        # Create a mapping for this date
        price_map = { (p[0], p[1]): float(p[2]) if p[2] is not None else "" for p in prices }
        
        # Map prices to the existing rows in the matrix
        df_matrix[d_str] = df_matrix.apply(lambda row: price_map.get((row['ticker'], row['exchange']), ""), axis=1)

    df_matrix.to_csv(filename, index=False)
    print(f"[SUCCESS] Wide Format: Added {len(new_dates)} columns and saved.")

def main():
    session = get_session()
    export_dir = "data_exports"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    
    start_time = datetime.datetime.now()
    smart_export_long(session, export_dir)
    smart_export_wide(session, export_dir)
    
    duration = (datetime.datetime.now() - start_time).total_seconds()
    print(f"\n[SUCCESS] SMART EXPORT COMPLETE in {duration:.2f} seconds.")
    session.close()

if __name__ == "__main__":
    main()
