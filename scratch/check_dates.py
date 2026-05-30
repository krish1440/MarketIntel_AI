import sys
import os
sys.path.append(os.getcwd())
from db.schema import get_session, Stock, HistoricalPrice
from sqlalchemy import func

session = get_session()
res = session.query(func.min(HistoricalPrice.date), func.max(HistoricalPrice.date)).first()
print(f"Date Range: {res}")
session.close()
