"""
MarketIntel AI: Symbol Discovery Engine
=======================================

This module acts as the "Mapmaker" for the system. It fetches the latest 
equity lists from the NSE and BSE, standardizes their symbols, and seeds 
the core 'stocks' table.

Key Features:
- NSE Equity List Discovery (via nsepython).
- BSE Equity List Discovery (via bsedata).
- Automated Ticker Standardizing (e.g., adding .NS/.BO suffixes).
- Idempotent Database Seeding.
"""

import sys
import os
import pandas as pd
import nsepython
from bsedata.bse import BSE

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.schema import get_session, Stock

def discover_nse_symbols():
    """
    Fetches the complete list of equity symbols from the NSE.

    Returns:
        list: A collection of symbol strings (e.g., ['RELIANCE', 'TCS']).
    """
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
    """
    Fetches the complete dictionary of stocks from the BSE.

    Returns:
        dict: A mapping of scrip codes to company names.
    """
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
    """
    Fetches all equity symbols on NSE for total market coverage.

    Returns:
        list: All discovered NSE equity symbols.
    """
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
    """
    Orchestrates the discovery and seeding of symbols into the database.

    Connects to NSE/BSE discovery services, standardizes suffixes for yfinance
    compatibility, and performs an idempotent upsert into the core stocks table.
    """
    session = get_session()
    
    # 1. NIFTY 500 / Total Market Update
    nse_symbols = discover_nifty_500()
    count_n = 0
    for sym in nse_symbols:
        # Standardize: yfinance expects uppercase
        sym = sym.upper()
        existing = session.query(Stock).filter_by(ticker=sym).first()
        if not existing:
            new_stock = Stock(
                ticker=sym,
                name=sym, # Default to ticker, cleaner than 'TICKER (NSE)'
                nse_symbol=f"{sym}.NS",
                bse_symbol=f"{sym}.BO" 
            )
            session.add(new_stock)
            count_n += 1
        else:
            if not existing.nse_symbol: existing.nse_symbol = f"{sym}.NS"
            if not existing.bse_symbol: existing.bse_symbol = f"{sym}.BO"

    session.commit()
    print(f"Database updated with {count_n} new stocks from NIFTY 500.")
    session.close()

    if count_n > 0:
        print("[AUTO-FIX] New stocks added. Running name resolution process...")
        try:
            from scripts.fix_stock_names import fix_names
            fix_names()
        except Exception as e:
            print(f"[AUTO-FIX] Error resolving names: {e}")

if __name__ == "__main__":
    update_database()

