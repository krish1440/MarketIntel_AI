"""
MARKETINTEL AI: REAL-TIME PRICE POLLER
======================================

This module implements a high-frequency polling engine that tracks live 
stock prices across the NSE and BSE. It captures 1-minute interval data 
and persists it to the 'live_quotes' table for dashboard visualization.

Key Features:
- 1-Minute Interval Polling.
- Batch Fetching (Chunked) to optimize API calls.
- Automated Intraday Change Percentage Calculation.
- Real-time DB persistence with conflict management.

Maintainer: MarketIntel AI Data Engineering
Version: 1.1.0
"""

import yfinance as yf
import time
import sys
import os
from datetime import datetime
import math

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, LiveQuote
from ingestion.alert_manager import AlertManager

def poll_prices():
    """Main execution loop for real-time price polling."""
    session = get_session()
    alert_mgr = AlertManager(session)
    
    while True:

        try:
            stocks = session.query(Stock).all()
            if not stocks:
                time.sleep(10)
                continue

            print(f"Polling {len(stocks)} companies across NSE & BSE...", flush=True)
            
            # Prepare batch lists
            nse_tickers = [s.nse_symbol for s in stocks if s.nse_symbol]
            bse_tickers = [s.bse_symbol for s in stocks if s.bse_symbol]
            
            # Chunking helper
            def chunk_list(lst, n):
                for i in range(0, len(lst), n):
                    yield lst[i:i + n]

            # 1. Batch Fetch NSE (Chunked)
            for chunk in chunk_list(nse_tickers, 100):
                print(f"Fetching chunk of {len(chunk)} NSE tickers...", flush=True)
                data_n = yf.download(chunk, period="1d", interval="1m", progress=False)
                if not data_n.empty and 'Close' in data_n:
                    close_data = data_n['Close']
                    open_data = data_n['Open'] if 'Open' in data_n else close_data
                    
                    for stock_sym in chunk:
                        if stock_sym in close_data:
                            series = close_data[stock_sym].dropna()
                            if not series.empty:
                                price = float(series.iloc[-1])
                                # Find stock in current session's list
                                stock = next((s for s in stocks if s.nse_symbol == stock_sym), None)
                                if stock and not math.isnan(price):
                                    prev_close = float(open_data[stock_sym].iloc[0])
                                    change = ((price / prev_close) - 1) * 100 if prev_close else 0
                                    
                                    quote = LiveQuote(
                                        stock_id=stock.id, exchange='NSE',
                                        price=price, change_percent=change
                                    )
                                    session.add(quote)
                                    # Check for watchlist alerts
                                    alert_mgr.check_price_alerts(stock.id, price, stock.ticker)

                session.commit()

            # 2. Batch Fetch BSE (Chunked)
            for chunk in chunk_list(bse_tickers, 100):
                print(f"Fetching chunk of {len(chunk)} BSE tickers...", flush=True)
                data_b = yf.download(chunk, period="1d", interval="1m", progress=False)
                if not data_b.empty and 'Close' in data_b:
                    close_data_b = data_b['Close']
                    open_data_b = data_b['Open'] if 'Open' in data_b else close_data_b
                    
                    for stock_sym in chunk:
                        if stock_sym in close_data_b:
                            series = close_data_b[stock_sym].dropna()
                            if not series.empty:
                                price = float(series.iloc[-1])
                                stock = next((s for s in stocks if s.bse_symbol == stock_sym), None)
                                if stock and not math.isnan(price):
                                    prev_close = float(open_data_b[stock_sym].iloc[0])
                                    change = ((price / prev_close) - 1) * 100 if prev_close else 0
                                    
                                    quote = LiveQuote(
                                        stock_id=stock.id, exchange='BSE',
                                        price=price, change_percent=change
                                    )
                                    session.add(quote)
                                    # Check for watchlist alerts
                                    alert_mgr.check_price_alerts(stock.id, price, stock.ticker)

                session.commit()

            print(f"Successfully updated all stocks at {datetime.now().strftime('%H:%M:%S')}", flush=True)
            time.sleep(60)
            
        except Exception as e:
            print(f"\nError in batch polling: {e}", flush=True)
            session.rollback()
            time.sleep(10)

if __name__ == "__main__":
    poll_prices()

