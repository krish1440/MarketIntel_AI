"""
MarketIntel AI: Leak-Free Signal Audit System
=============================================

This script performs a 7-day walk-forward audit of the technical signals 
and AI predictions. It ensures NO DATA LEAKAGE by slicing the historical 
data chronologically before generating each signal.
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice
from models.preprocess import calculate_technical_indicators
from intelligence.prediction_service import PredictionService

def run_audit(ticker, days=7):
    session = get_session()
    try:
        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock: return None
        
        # 1. Fetch full history for calculations
        prices = pd.read_sql(
            session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.asc()).statement,
            session.bind
        )
        
        if len(prices) < 100: return None
        
        audit_results = []
        
        # 2. Walk-forward testing (Loop through the last N days)
        # We start from 'days' ago and stop 1 day before current to allow outcome check
        for i in range(days, 1, -1):
            # Target date for signal generation
            # Slice data: Only everything BEFORE (and including) this day
            cut_off_idx = len(prices) - i
            historical_slice = prices.iloc[:cut_off_idx+1].copy()
            target_date = historical_slice.iloc[-1]['date']
            
            # Outcome window: 1-3 days AFTER the cut_off
            outcome_slice = prices.iloc[cut_off_idx+1 : cut_off_idx+4]
            if outcome_slice.empty: continue
            
            current_price = historical_slice.iloc[-1]['close']
            next_price = outcome_slice.iloc[0]['close']
            max_future = outcome_slice['high'].max()
            
            # Generate Signal using the logic (Rule-based or Model)
            # For audit, we'll manually apply the logic from PredictionService to ensure no leakage
            # or we can mock the PredictionService to use this slice.
            
            # Calculate Indicators on the slice ONLY
            tech_df = calculate_technical_indicators(historical_slice)
            latest = tech_df.iloc[-1]
            
            # Extract confluence score (Synced with PredictionService refinement)
            score = 0
            rsi = latest['RSI_14']
            sma_20 = latest['SMA_20']
            adx = latest.get('ADX_14', 0)
            cci = latest.get('CCI_20', 0)
            macd = latest.get('MACD', 0)
            macd_signal = latest.get('MACD_Signal', 0)
            vwap = latest.get('VWAP', 0)
            tenkan = latest.get('Ichimoku_Tenkan', 0)
            kijun = latest.get('Ichimoku_Kijun', 0)
            
            if rsi < 30: score += 2
            if rsi > 70: score -= 2
            
            if adx > 25:
                if current_price > sma_20: score += 1
                elif current_price < sma_20: score -= 1
            
            if cci > 150: score += 1
            if cci < -150: score -= 1
            
            if current_price > tenkan and tenkan > kijun: score += 2
            if current_price < tenkan and tenkan < kijun: score -= 2
            
            if score < 0:
                if current_price < vwap: score -= 1
                if macd < macd_signal: score -= 1
                if rsi < 35: score += 2 # Oversold protection
            
            signal = "BUY" if score >= 2 else ("SELL" if score <= -3 else "HOLD")
            
            # Verification: Was the signal correct?
            # BUY is correct if price goes up in the next 1-3 days
            is_correct = False
            if signal == "BUY" and max_future > current_price: is_correct = True
            elif signal == "SELL" and next_price < current_price: is_correct = True
            elif signal == "HOLD": is_correct = True # Neutral
            
            audit_results.append({
                "date": target_date.strftime('%Y-%m-%d'),
                "price": current_price,
                "signal": signal,
                "score": score,
                "next_day": next_price,
                "win": is_correct
            })
            
        return audit_results
    finally:
        session.close()

def run_bulk_audit(output_file="data_exports/signal_audit_report.csv", limit=None):
    session = get_session()
    stocks = session.query(Stock).all()
    if limit: stocks = stocks[:limit]
    
    all_results = []
    print(f"Starting Bulk Audit for {len(stocks)} stocks...")
    
    for i, stock in enumerate(stocks):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(stocks)} stocks processed...")
            
        res = run_audit(stock.ticker)
        if res:
            for r in res:
                # Calculate return % for the signal
                # For BUY: (NextDay - Price) / Price
                # For SELL: (Price - NextDay) / Price
                ret = 0.0
                if r['signal'] == 'BUY':
                    ret = (r['next_day'] - r['price']) / r['price']
                elif r['signal'] == 'SELL':
                    ret = (r['price'] - r['next_day']) / r['price']
                
                r['return_pct'] = float(ret * 100)
                r['ticker'] = stock.ticker
                all_results.append(r)
                
    if all_results:
        df = pd.DataFrame(all_results)
        cols = ['ticker', 'date', 'price', 'signal', 'score', 'next_day', 'return_pct', 'win']
        df = df[cols]
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False)
        
        print("\n" + "="*50)
        print("INSTITUTIONAL SIGNAL AUDIT REPORT")
        print("="*50)
        
        # Summary Metrics
        total_signals = len(df)
        active_signals = len(df[df['signal'] != 'HOLD'])
        density = (active_signals / total_signals) * 100 if total_signals > 0 else 0
        
        print(f"Total Samples  : {total_signals}")
        print(f"Signal Density : {density:.1f}% (Active vs Hold)")
        print(f"Global Accuracy: {(df['win'].sum()/total_signals)*100:.1f}%")
        
        # Performance by Signal Type
        print("\n--- Signal Fidelity Breakdown ---")
        metrics = []
        for sig in ['BUY', 'SELL', 'HOLD']:
            sig_df = df[df['signal'] == sig]
            if sig_df.empty: continue
            
            # Precision: Wins / Total of this signal
            precision = (sig_df['win'].sum() / len(sig_df)) * 100
            
            # Avg Return
            avg_ret = sig_df['return_pct'].mean()
            
            print(f"{sig:6} | Precision: {precision:5.1f}% | Avg Return: {avg_ret:6.2f}% | Count: {len(sig_df)}")
            
            metrics.append({
                "signal": sig,
                "precision": precision,
                "avg_return": avg_ret,
                "count": len(sig_df)
            })
            
        # Overall Profit Factor (Simulated)
        total_ret = df[df['signal'] != 'HOLD']['return_pct'].sum()
        print(f"\nSimulated Week Alpha: {total_ret:.2f}% (Cumulative across universe)")
        print("="*50)
        
        # Save summary to JSON for API
        summary = {
            "total_samples": total_signals,
            "density": float(density),
            "accuracy": float((df['win'].sum()/total_signals)*100),
            "signals": metrics,
            "alpha": float(total_ret),
            "last_audit": datetime.now().isoformat()
        }
        with open('data_exports/audit_summary.json', 'w') as f:
            json.dump(summary, f)
            
    else:
        print("No results generated.")

if __name__ == "__main__":
    import json
    if len(sys.argv) > 1 and sys.argv[1] == "--bulk":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        run_bulk_audit(limit=limit)
    else:
        ticker_to_audit = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
        print(f"--- Starting Leak-Free Audit for {ticker_to_audit} (Last 7 Days) ---")
        
        results = run_audit(ticker_to_audit)
        
        if not results:
            print("Error: No data available for audit.")
        else:
            df_res = pd.DataFrame(results)
            print(df_res.to_string(index=False))
            wins = sum(1 for r in results if r['win'])
            print(f"\n✅ Audit Complete. Accuracy: {(wins/len(results))*100:.1f}%")
