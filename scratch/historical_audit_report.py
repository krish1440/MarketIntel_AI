
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, HistoricalFundamentals, NewsArticle
from models.preprocess import calculate_technical_indicators

def run_leak_free_audit(ticker, start_date, end_date):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock: return None

    print(f"--- Leak-Free System Audit: {ticker} ---")
    
    # 1. Pre-calculate indicators (inherently leak-free at index T)
    all_prices = pd.read_sql(
        session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.asc()).statement,
        session.bind
    )
    all_prices = calculate_technical_indicators(all_prices)
    all_prices['date_only'] = pd.to_datetime(all_prices['date']).dt.date
    
    target_start = datetime.strptime(start_date, '%Y-%m-%d').date()
    target_end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    audit_indices = all_prices[(all_prices['date_only'] >= target_start) & 
                               (all_prices['date_only'] <= target_end)].index.tolist()
    
    audit_rows = []
    for idx in audit_indices:
        row = all_prices.loc[idx]
        d = row['date_only']
        
        # Fundamental Fetch (Leak-Free)
        fund = session.query(HistoricalFundamentals).filter(
            HistoricalFundamentals.stock_id == stock.id,
            HistoricalFundamentals.date <= d
        ).order_by(HistoricalFundamentals.date.desc()).first()
        
        # Sentiment Fetch (Leak-Free)
        news = session.query(NewsArticle).filter(
            NewsArticle.stock_id == stock.id,
            NewsArticle.published_at <= datetime.combine(d, datetime.min.time())
        ).order_by(NewsArticle.published_at.desc()).limit(5).all()
        sent_scores = [n.sentiment_score for n in news if n.sentiment_score is not None]
        avg_sent = float(sum(sent_scores)/len(sent_scores)) if sent_scores else 0.0
        
        # Signal Reconstruction
        score = 0
        rsi = float(row.get('RSI_14', 50))
        adx = float(row.get('ADX_14', 0))
        close = float(row['close'])
        vwap = float(row.get('VWAP', close))
        pe = float(fund.pe_ratio) if fund and fund.pe_ratio else 25.0
        
        if rsi < 35: score += 2
        if rsi > 65: score -= 2
        if close > vwap: score += 1
        if close < vwap: score -= 1
        if pe < 20: score += 1
        if pe > 45: score -= 1
        if avg_sent > 0.3: score += 1
        if avg_sent < -0.3: score -= 1
        
        signal = "BUY" if score >= 3 else ("SELL" if score <= -3 else "HOLD")
        
        # Outcome (Look-Ahead 20 Days)
        if idx + 20 < len(all_prices):
            outcome = all_prices.loc[idx+1:idx+20]
            max_p = float(outcome['high'].max())
            min_p = float(outcome['low'].min())
            end_p = float(outcome.iloc[-1]['close'])
            
            p_potential = ((max_p - close) / close) * 100
            m_ret = ((end_p - close) / close) * 100
            
            win = "False"
            if signal == "BUY" and (p_potential > 5.0 or m_ret > 2.0): win = "True"
            elif signal == "SELL" and (m_ret < -2.0): win = "True"
            elif signal == "HOLD" and (abs(m_ret) < 3.0): win = "True"
            
            audit_rows.append({
                "Date": d.strftime('%Y-%m-%d'),
                "Price": round(close, 1),
                "PE": round(pe, 1),
                "Sent": round(avg_sent, 2),
                "Score": score,
                "Signal": signal,
                "Win": "Win" if win == "True" else "Loss",
                "MaxProfit": f"{p_potential:.1f}%",
                "Return": f"{m_ret:.1f}%"
            })

    session.close()
    if audit_rows:
        df = pd.DataFrame(audit_rows)
        print(df.to_string(index=False))
        acc = (df['Win'] == "Win").sum() / len(df) * 100
        print(f"\nAudit Accuracy: {acc:.1f}%")

if __name__ == "__main__":
    run_leak_free_audit("TCS", "2026-04-01", "2026-04-20")
