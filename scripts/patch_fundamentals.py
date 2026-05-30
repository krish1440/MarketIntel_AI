import sys
import os
import yfinance as yf

sys.path.append(os.getcwd())
from db.schema import get_session, Stock

def patch_fundamentals(ticker="CIPLA"):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock:
        print(f"Ticker {ticker} not found in database.")
        session.close()
        return
        
    print(f"Fetching fundamentals for {ticker} from yfinance...")
    try:
        ticker_str = stock.nse_symbol if stock.nse_symbol else f"{stock.ticker}.NS"
        yt = yf.Ticker(ticker_str)
        info = yt.info
        
        real_name = info.get('longName') or info.get('shortName') or stock.name
        sector = info.get('sector') or 'Unknown'
        pe_ratio = info.get('trailingPE') or info.get('forwardPE') or 0.0
        market_cap = info.get('marketCap') or 0
        eps = info.get('trailingEps') or 0.0
        
        print(f"Resolved details for {ticker}:")
        print(f"  Name: {real_name}")
        print(f"  Sector: {sector}")
        print(f"  P/E Ratio: {pe_ratio}")
        print(f"  Market Cap: {market_cap}")
        
        stock.name = real_name
        stock.sector = sector
        stock.pe_ratio = pe_ratio
        stock.market_cap = market_cap
        stock.eps = eps
        
        session.commit()
        print("Successfully updated database.")
    except Exception as e:
        print(f"Error fetching fundamentals: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    ticker = "CIPLA"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    patch_fundamentals(ticker)
