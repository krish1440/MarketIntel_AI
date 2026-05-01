"""
MarketIntel AI: Smart Additive Export Engine
============================================
Handles high-performance, incremental exports of institutional datasets 
for Kaggle. Implements 'Additive Logic' to minimize disk I/O and DB overhead.

Operational Streams:
1. Long Format (OHLCV): Reads last file date and appends only newer rows.
2. Wide Format (Matrix): Uses Pandas to merge new date columns into 
   the existing historical price grid.

This engine is designed for daily production use, reducing export time 
from minutes to seconds.
"""
import sys
import os
import csv
import pandas as pd
import datetime

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, HistoricalPrice, Stock
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()


def smart_export_long(session, export_dir):
    """
    Additive export for Long Format: Appends only new rows since the last date in the CSV.

    This function performs a 'tail-read' on the existing CSV to identify the 
    most recent record, then queries the database for all subsequent entries 
    to append them in a single I/O operation.

    Args:
        session (sqlalchemy.orm.Session): The active database session.
        export_dir (str): The destination directory for the generated CSV.

    Returns:
        None: The output is appended directly to the existing file.
    """
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
    """
    Additive export for Wide Format: Adds new date columns to the existing matrix.

    Uses Pandas to load the existing time-series grid and dynamically 
    introduces new date columns by mapping database price points 
    to existing stock/exchange identifiers.

    Args:
        session (sqlalchemy.orm.Session): The active database session.
        export_dir (str): The destination directory for the generated CSV.

    Returns:
        None: The output is saved back to the matrix file.
    """
    filename = os.path.join(export_dir, "indian_stocks_time_series_matrix.csv")
    
    if not os.path.exists(filename):
        print("[INFO] Wide Format: No existing matrix found. Rebuilding full matrix from DB...")
        
        # 1. Get all dates and stocks
        all_dates = [d[0].isoformat() for d in session.query(HistoricalPrice.date).distinct().order_by(HistoricalPrice.date.asc()).all()]
        stocks = session.query(Stock.ticker, Stock.id).all()
        
        # 2. Initialize matrix
        data = []
        for ticker, s_id in stocks:
            # We need exchange too, so let's get unique (ticker, exchange) pairs
            exchanges = [e[0] for e in session.query(HistoricalPrice.exchange).filter(HistoricalPrice.stock_id == s_id).distinct().all()]
            for ex in exchanges:
                data.append({'ticker': ticker, 'exchange': ex})
        
        df_matrix = pd.DataFrame(data)
        
        # 3. Fill dates (initially empty)
        for d_str in all_dates:
            df_matrix[d_str] = ""
            
        # 4. Fill prices
        prices = session.query(Stock.ticker, HistoricalPrice.exchange, HistoricalPrice.date, HistoricalPrice.close)\
                        .join(HistoricalPrice).all()
        
        # Pivot manually or via dict for speed
        price_dict = {}
        for t, ex, d, c in prices:
            price_dict[(t, ex, d.isoformat())] = float(c) if c is not None else ""
            
        def get_price(row, date_str):
            return price_dict.get((row['ticker'], row['exchange'], date_str), "")
            
        for d_str in all_dates:
            df_matrix[d_str] = df_matrix.apply(lambda r: get_price(r, d_str), axis=1)
            
        df_matrix.to_csv(filename, index=False)
        print(f"[SUCCESS] Wide Format: Full matrix rebuilt with {len(all_dates)} dates.")
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

import json
import subprocess

def push_to_kaggle(export_dir):
    """
    Automates the Kaggle dataset versioning process.
    """
    print("\n[KAGGLE] Preparing to push to Kaggle...")
    
    # 1. Create/Update metadata
    metadata = {
        "id": "krishchaudhary14/indian-stock-market-full-5-year-history",
        "title": "Indian Stock Market: Full 5-Year History",
        "licenses": [{"name": "CC0-1.0"}]
    }
    
    metadata_path = os.path.join(export_dir, "dataset-metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[KAGGLE] Metadata generated at {metadata_path}")
    
    # 2. Find Kaggle Executable (Windows specific fix)
    kaggle_exe = "kaggle"
    if os.name == 'nt':
        # Try to find it in common Python Scripts folders if 'kaggle' fails
        scripts_path = os.path.join(os.environ.get('APPDATA', ''), 'Python', 'Python312', 'Scripts', 'kaggle.exe')
        local_scripts = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python312', 'Scripts', 'kaggle.exe')
        
        if os.path.exists(local_scripts):
            kaggle_exe = local_scripts
        elif os.path.exists(scripts_path):
            kaggle_exe = scripts_path
            
    # 3. Push Version
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Daily Automated Market Update ({timestamp})"
        
        print(f"[KAGGLE] Pushing new version using: {kaggle_exe}")
        result = subprocess.run(
            [kaggle_exe, "datasets", "version", "-p", export_dir, "-m", message],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f"[SUCCESS] Kaggle Dataset updated successfully!")
            print(result.stdout)
        else:
            print(f"[ERROR] Kaggle Upload failed: {result.stderr}")
            
    except Exception as e:
        print(f"[ERROR] Unexpected error during Kaggle push: {e}")


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
    
    # Auto-Upload to Kaggle
    push_to_kaggle(export_dir)
    
    session.close()

if __name__ == "__main__":
    main()

