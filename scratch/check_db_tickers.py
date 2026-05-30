import sys
import os
sys.path.append(os.getcwd())
from db.schema import get_session, Stock, HistoricalPrice

session = get_session()
stocks = session.query(Stock).all()
print(f"Total stocks in DB: {len(stocks)}")
for s in stocks[:20]:
    cnt = session.query(HistoricalPrice).filter_by(stock_id=s.id).count()
    print(f"Ticker: {s.ticker}, Name: {s.name}, Count: {cnt}")
session.close()
