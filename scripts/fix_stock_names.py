import sys
import os
import yfinance as yf
from tqdm import tqdm

sys.path.append(os.getcwd())
from db.schema import get_session, Stock

def fix_names():
    session = get_session()
    # Audit ALL stocks to ensure 100% accurate naming
    stocks_to_fix = session.query(Stock).all()
    
    print(f"Found {len(stocks_to_fix)} stocks needing name correction.")
    
    fixed_count = 0
    # We'll process in batches to avoid overwhelming yfinance or the DB
    for stock in tqdm(stocks_to_fix):
        try:
            # Try NSE symbol first
            ticker_str = stock.nse_symbol if stock.nse_symbol else f"{stock.ticker}.NS"
            yt = yf.Ticker(ticker_str)
            info = yt.info
            
            real_name = info.get('longName') or info.get('shortName')
            
            if real_name:
                stock.name = real_name
                fixed_count += 1
                
                # Commit every 20 stocks to save progress
                if fixed_count % 20 == 0:
                    session.commit()
            else:
                # If yfinance fails, at least remove the (NSE) part
                stock.name = stock.name.replace(" (NSE)", "").strip()
                
        except Exception as e:
            # Fallback cleanup
            stock.name = stock.name.replace(" (NSE)", "").strip()
            continue

    session.commit()
    print(f"Successfully updated {fixed_count} stock names.")
    session.close()

if __name__ == "__main__":
    fix_names()
