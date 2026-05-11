import yfinance as yf
from db.schema import get_session, Stock
import time

def update_stock_fundamentals(limit=100):
    """
    Fetches and updates fundamental financial data for stocks in the database.
    Uses yfinance to pull real-time institutional metrics.
    """
    session = get_session()
    stocks = session.query(Stock).filter(Stock.pe_ratio == None).limit(limit).all()
    
    print(f"--- Starting Fundamental Data Update for {len(stocks)} stocks ---")
    
    count = 0
    for stock in stocks:
        ticker = stock.nse_symbol or f"{stock.ticker}.NS"
        print(f"Fetching {ticker}...")
        
        try:
            yticker = yf.Ticker(ticker)
            info = yticker.info
            
            stock.pe_ratio = info.get('trailingPE') or info.get('forwardPE')
            stock.market_cap = info.get('marketCap')
            stock.eps = info.get('trailingEps')
            stock.sector = info.get('sector')
            stock.revenue_growth = info.get('revenueGrowth')
            stock.debt_to_equity = info.get('debtToEquity')
            
            # Record historical snapshot
            from db.schema import HistoricalFundamentals
            import datetime
            hist = HistoricalFundamentals(
                stock_id=stock.id,
                date=datetime.date.today(),
                pe_ratio=stock.pe_ratio,
                eps=stock.eps,
                market_cap=stock.market_cap,
                revenue_growth=stock.revenue_growth,
                debt_to_equity=stock.debt_to_equity
            )
            session.add(hist)
            
            session.commit()
            count += 1
            print(f"  [SUCCESS] PE: {stock.pe_ratio}, Sector: {stock.sector}")
            
        except Exception as e:
            print(f"  [ERROR] Could not fetch data for {ticker}: {str(e)}")
            session.rollback()
            
        # Rate limiting safety
        time.sleep(0.5)
        
    print(f"\n--- Update Complete. Updated {count} stocks. ---")
    session.close()

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    update_stock_fundamentals(limit=limit)
