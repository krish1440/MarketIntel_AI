import sys
import os
import pandas as pd
import nsepython
from bsedata.bse import BSE

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.schema import get_session, Stock

def discover_nse_symbols():
    print("Fetching NSE Equity list...")
    try:
        df = nsepython.nse_eqlist()
        symbols = df['SYMBOL'].tolist()
        print(f"Found {len(symbols)} stocks on NSE.")
        return symbols
    except Exception as e:
        print(f"Error fetching NSE symbols: {e}")
        return []

def discover_bse_symbols():
    print("Fetching BSE Equity list...")
    try:
        b = BSE()
        stocks = b.get_all_stocks()
        print(f"Found {len(stocks)} stocks on BSE.")
        return stocks
    except Exception as e:
        print(f"Error fetching BSE symbols: {e}")
        return {}

def discover_nifty_500():
    print("Fetching NSE Equity symbols...")
    try:
        # nse_eq_symbols returns a list of all equity symbols on NSE
        all_symbols = nsepython.nse_eq_symbols()
        # Use ALL symbols for total market coverage
        symbols = all_symbols
        print(f"Found {len(all_symbols)} total stocks. Adding ALL to the system.")
        return symbols
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []

def update_database():
    session = get_session()
    
    # 1. NIFTY 500 Update
    nse_symbols = discover_nifty_500()
    count_n = 0
    for sym in nse_symbols:
        # Standardize: yfinance expects uppercase
        sym = sym.upper()
        existing = session.query(Stock).filter_by(ticker=sym).first()
        if not existing:
            new_stock = Stock(
                ticker=sym,
                name=f"{sym} (NSE)",
                nse_symbol=f"{sym}.NS",
                bse_symbol=f"{sym}.BO" # Most Nifty 500 stocks share the same ticker on BSE
            )
            session.add(new_stock)
            count_n += 1
        else:
            if not existing.nse_symbol: existing.nse_symbol = f"{sym}.NS"
            if not existing.bse_symbol: existing.bse_symbol = f"{sym}.BO"

    session.commit()
    print(f"Database updated with {count_n} new stocks from NIFTY 500.")
    session.close()

if __name__ == "__main__":
    update_database()
