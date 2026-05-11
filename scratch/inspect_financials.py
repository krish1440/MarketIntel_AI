
import yfinance as yf
import pandas as pd

def inspect_financials(ticker_symbol):
    print(f"--- Inspecting Financials for {ticker_symbol} ---")
    yt = yf.Ticker(ticker_symbol)
    
    print("\n[QUARTERLY FINANCIALS]")
    print(yt.quarterly_financials.columns)
    
    print("\n[ANNUAL FINANCIALS]")
    print(yt.financials.columns)
    
    # Check EPS
    if not yt.financials.empty:
        eps_col = [c for c in yt.financials.index if 'EPS' in c.upper()]
        print(f"\n[ANNUAL EPS INDEX]: {eps_col}")
        if eps_col:
            print(yt.financials.loc[eps_col[0]])

if __name__ == "__main__":
    inspect_financials("TCS.NS")
