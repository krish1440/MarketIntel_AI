from db.schema import get_session, Stock, HistoricalPrice, HistoricalFundamentals
session = get_session()
print(f"Total Stocks: {session.query(Stock).count()}")
print(f"Total Prices: {session.query(HistoricalPrice).count()}")
print(f"Total Fundamentals: {session.query(HistoricalFundamentals).count()}")
session.close()
