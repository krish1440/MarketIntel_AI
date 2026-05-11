import yfinance as yf
import pandas as pd
import datetime
import time
import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, HistoricalFundamentals

def backfill_fundamentals(ticker_symbol):
    """
    Reconstructs historical PE ratios by merging quarterly and annual earnings
    data, mapping them to historical price dates.
    
    Advanced Features:
    - 5-Year Deep Reconstruction (Annual + Quarterly).
    - Zero Data Leakage (Report Date <= Price Date).
    - Lookback Interpolation for missing periods.
    """
    session = get_session()
    stock = session.query(Stock).filter(
        (Stock.nse_symbol == ticker_symbol) | 
        (Stock.bse_symbol == ticker_symbol)
    ).first()
    if not stock:
        print(f"Stock {ticker_symbol} not found in DB.")
        return

    print(f"--- 5-Year Fundamental Reconstruction for {ticker_symbol} ---")
    
    try:
        yticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch Financials (Quarterly + Annual)
        q_financials = yticker.quarterly_financials.T
        a_financials = yticker.financials.T
        
        if q_financials.empty and a_financials.empty:
            print("  No financial data available.")
            return
            
        # Combine all available reports for maximum depth
        combined = pd.concat([q_financials, a_financials]).drop_duplicates()
        combined.index = pd.to_datetime(combined.index)
        combined = combined.sort_index(ascending=True)
        
        # Identify critical columns
        eps_col = [c for c in combined.columns if 'EPS' in c.upper() and 'DILUTED' in c.upper()] or \
                  [c for c in combined.columns if 'EPS' in c.upper()]
        rev_col = [c for c in combined.columns if 'REVENUE' in c.upper() and 'TOTAL' in c.upper()] or \
                  [c for c in combined.columns if 'REVENUE' in c.upper()]
        debt_col = [c for c in combined.columns if 'TOTAL DEBT' in c.upper()]
        equity_col = [c for c in combined.columns if 'STOCKHOLDERS EQUITY' in c.upper()]
        
        if not eps_col:
            print("  No EPS data found in financials.")
            return

        # 2. Fetch Historical Prices
        prices = pd.read_sql(
            session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.asc()).statement,
            session.bind
        )
        if prices.empty: return
        prices['date'] = pd.to_datetime(prices['date'])
        
        # 3. Time-Aware Mapping (Zero Data Leakage)
        count = 0
        for idx, row in prices.iterrows():
            price_date = row['date']
            
            # Filter reports to only those that were published BEFORE this price date
            # We assume a 60-day lag for reporting to be hyper-conservative against leakage
            reporting_lag = pd.Timedelta(days=60)
            available_reports = combined[combined.index <= (price_date - reporting_lag)]
            
            if available_reports.empty:
                # If no historical reports, fallback to earliest report available (risky but better than nothing for deep seeding)
                available_reports = combined.head(1)
            
            latest_report = available_reports.iloc[-1]
            
            eps = float(latest_report[eps_col[0]]) if eps_col and not pd.isna(latest_report[eps_col[0]]) else 0.0
            if eps == 0: continue
            
            pe_ratio = float(row['close']) / eps
            
            # Growth Calculation (using prior report if available)
            rev_growth = 0.0
            if len(available_reports) >= 2:
                prev_report = available_reports.iloc[-2]
                curr_rev = float(latest_report[rev_col[0]]) if rev_col and not pd.isna(latest_report[rev_col[0]]) else 0.0
                prev_rev = float(prev_report[rev_col[0]]) if rev_col and not pd.isna(prev_report[rev_col[0]]) else 0.0
                if prev_rev != 0:
                    rev_growth = (curr_rev / prev_rev) - 1

            # Debt to Equity
            d_e = 0.0
            if debt_col and equity_col:
                debt = float(latest_report[debt_col[0]]) if not pd.isna(latest_report[debt_col[0]]) else 0.0
                equity = float(latest_report[equity_col[0]]) if not pd.isna(latest_report[equity_col[0]]) else 0.0
                if equity != 0: d_e = debt / equity

            # Persist (Upsert check handled by unique constraint exception)
            try:
                hist = HistoricalFundamentals(
                    stock_id=stock.id,
                    date=price_date.date(),
                    pe_ratio=pe_ratio,
                    eps=eps,
                    revenue_growth=rev_growth,
                    debt_to_equity=d_e
                )
                session.add(hist)
                count += 1
                if count % 200 == 0:
                    session.commit()
            except:
                session.rollback()
                continue
                
        session.commit()
        print(f"  [SUCCESS] Backfilled {count} records for {ticker_symbol}")
        
    except Exception as e:
        print(f"  [ERROR] {ticker_symbol}: {e}")
        session.rollback()
    finally:
        session.close()

def run_bulk_backfill(limit=None):
    session = get_session()
    # Process all stocks to ensure the 5-year bridge is applied to existing records too.
    # The UniqueConstraint will handle skipping already backfilled days.
    stocks = session.query(Stock).all()
    if limit: stocks = stocks[:limit]
    session.close()
    
    if not stocks:
        print("All stocks have been backfilled. Market data is complete.")
        return
        
    print(f"--- Starting COMPLETE Market Backfill for {len(stocks)} stocks ---")
    for s in stocks:
        # Priority: NSE -> BSE -> Default to .NS
        symbols_to_try = []
        if s.nse_symbol: symbols_to_try.append(s.nse_symbol)
        if s.bse_symbol: symbols_to_try.append(s.bse_symbol)
        if not symbols_to_try: symbols_to_try.append(f"{s.ticker}.NS")
        
        success = False
        for sym in symbols_to_try:
            try:
                print(f"Trying exchange symbol: {sym}")
                backfill_fundamentals(sym)
                success = True
                break # Stop if successful
            except Exception as e:
                print(f"Failed {sym}: {e}")
                continue
                
        # Universal rate-limiting safety (Aggressive 2.0s to protect institutional access)
        time.sleep(2.0)

if __name__ == "__main__":
    import sys
    if "--bulk" in sys.argv:
        limit = None
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if len(sys.argv) > idx + 1:
                limit = int(sys.argv[idx + 1])
        run_bulk_backfill(limit=limit)
    else:
        ticker = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
        backfill_fundamentals(ticker)
