
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, HistoricalFundamentals

def run_long_term_audit(ticker, sample_years=3):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return None

    print(f"--- Long-Term Institutional Audit: {ticker} ---")
    
    all_prices = pd.read_sql(
        session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.asc()).statement,
        session.bind
    )
    all_prices['SMA_50'] = all_prices['close'].rolling(window=50).mean()
    all_prices['SMA_200'] = all_prices['close'].rolling(window=200).mean()
    all_prices['date_only'] = pd.to_datetime(all_prices['date']).dt.date
    
    start_date = (datetime.now() - timedelta(days=365 * sample_years)).date()
    audit_dates = all_prices[all_prices['date_only'] >= start_date]['date_only'].tolist()[::60]
    
    audit_rows = []
    for d in audit_dates:
        row = all_prices[all_prices['date_only'] == d].iloc[0]
        idx = all_prices[all_prices['date_only'] == d].index[0]
        
        fund = session.query(HistoricalFundamentals).filter(
            HistoricalFundamentals.stock_id == stock.id,
            HistoricalFundamentals.date <= d
        ).order_by(HistoricalFundamentals.date.desc()).first()
        
        pe = float(fund.pe_ratio) if fund and fund.pe_ratio else 25.0
        rev_growth = float(fund.revenue_growth) if fund and fund.revenue_growth else 0.0
        
        score = 0
        close = float(row['close'])
        sma_50 = float(row['SMA_50']) if not pd.isna(row['SMA_50']) else close
        sma_200 = float(row['SMA_200']) if not pd.isna(row['SMA_200']) else close
        
        if close > sma_200: score += 2
        if sma_50 > sma_200: score += 1
        if rev_growth > 0.10: score += 2
        if pe < 30: score += 1
        
        signal = "ACCUMULATE" if score >= 3 else ("REDUCE" if score <= 0 else "HOLD")
        
        if idx + 126 < len(all_prices):
            future_price = float(all_prices.loc[idx + 126]['close'])
            six_month_ret = ((future_price - close) / close) * 100
            
            audit_rows.append({
                "Entry_Date": d.strftime('%Y-%m-%d'),
                "Entry_Price": f"{close:,.0f}",
                "PE": f"{pe:.1f}",
                "Growth": f"{rev_growth*100:.1f}%",
                "Signal": signal,
                "Outcome_6M": f"{six_month_ret:+.1f}%"
            })

    session.close()
    if audit_rows:
        df = pd.DataFrame(audit_rows)
        print(df.to_string(index=False))
        return df
    return None

if __name__ == "__main__":
    for t in ["TCS", "INFY", "RELIANCE"]:
        run_long_term_audit(t, sample_years=3)
        print("\n" + "-"*60 + "\n")
