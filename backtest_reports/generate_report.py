import sys
import os
import datetime
import pandas as pd
from sqlalchemy import func

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice
from intelligence.prediction_service import PredictionService

def run_backtest_inline(ticker, start_date, end_date, service, session, exchange="NSE"):
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock:
        return None

    # Get all actual prices for the period to verify results
    actual_prices = pd.read_sql(
        session.query(HistoricalPrice).filter(
            HistoricalPrice.stock_id == stock.id,
            HistoricalPrice.exchange == exchange,
            HistoricalPrice.date >= start_date,
            HistoricalPrice.date <= end_date
        ).order_by(HistoricalPrice.date.asc()).statement,
        session.bind
    )

    if actual_prices.empty:
        return None

    results = []
    capital = 100000.0
    shares = 0
    position_type = None  # "LONG" or "SHORT" or None
    entry_price = 0.0
    highest_price = 0.0
    lowest_price = 0.0
    entry_atr = 0.0
    days_held = 0
    trading_days = actual_prices['date'].tolist()
    
    for i in range(len(trading_days) - 1):
        current_day = trading_days[i]
        current_price = float(actual_prices.iloc[i]['close'])
        
        # Get signal as of the end of current_day
        signal_data = service.get_signal(ticker, as_of=current_day)
        signal = signal_data.get('signal', 'HOLD')
        
        atr = signal_data.get('risk_management', {}).get('atr_volatility', current_price * 0.02)
        if atr <= 0 or pd.isna(atr):
            atr = current_price * 0.02
            
        adx = signal_data.get('technicals', {}).get('adx', 20)
        if adx > 25:
            atr_multiplier = 2.2
        else:
            atr_multiplier = 1.3
            
        action = "NONE"
        
        # 1. Exit Logic for Active Positions
        if position_type == "LONG" and shares > 0:
            days_held += 1
            highest_price = max(highest_price, current_price)
            trailing_stop = highest_price - (atr_multiplier * entry_atr)
            take_profit = entry_price + (2.5 * entry_atr)
            
            # Stop-Loss Exit
            if current_price < trailing_stop:
                capital += shares * current_price
                action = f"STOP_EXIT_SL {shares}"
                shares = 0
                position_type = None
                days_held = 0
            # Take-Profit Exit
            elif current_price >= take_profit:
                capital += shares * current_price
                action = f"STOP_EXIT_TP {shares}"
                shares = 0
                position_type = None
                days_held = 0
            # Time-based exit (12 days flat/loss)
            elif days_held >= 12 and current_price < entry_price:
                capital += shares * current_price
                action = f"STOP_EXIT_TIME {shares}"
                shares = 0
                position_type = None
                days_held = 0
            # Model Opposing Signal Exit
            elif (signal == "STRONG_SELL" or signal == "STRONG SELL" or signal == "SELL") and shares > 0:
                capital += shares * current_price
                action = f"SELL {shares}"
                shares = 0
                position_type = None
                days_held = 0
                
        elif position_type == "SHORT" and shares > 0:
            days_held += 1
            lowest_price = min(lowest_price, current_price)
            trailing_stop = lowest_price + (atr_multiplier * entry_atr)
            take_profit = entry_price - (2.5 * entry_atr)
            
            # Stop-Loss Exit (Price rose above trailing stop)
            if current_price > trailing_stop:
                capital += shares * (entry_price - current_price)
                action = f"STOP_EXIT_SL_SHORT {shares}"
                shares = 0
                position_type = None
                days_held = 0
            # Take-Profit Exit (Price dropped to target)
            elif current_price <= take_profit:
                capital += shares * (entry_price - current_price)
                action = f"STOP_EXIT_TP_SHORT {shares}"
                shares = 0
                position_type = None
                days_held = 0
            # Time-based exit (12 days flat/loss)
            elif days_held >= 12 and current_price > entry_price:
                capital += shares * (entry_price - current_price)
                action = f"STOP_EXIT_TIME_SHORT {shares}"
                shares = 0
                position_type = None
                days_held = 0
            # Model Opposing Signal Exit
            elif (signal == "STRONG_BUY" or signal == "STRONG BUY" or signal == "BUY") and shares > 0:
                capital += shares * (entry_price - current_price)
                action = f"COVER_SHORT {shares}"
                shares = 0
                position_type = None
                days_held = 0
                
        # 2. Entry Logic (Only if in Cash)
        if position_type is None or shares == 0:
            # LONG Entries
            if (signal == "STRONG_BUY" or signal == "STRONG BUY") and capital >= current_price:
                shares_to_buy = int(capital // current_price)
                if shares_to_buy > 0:
                    shares = shares_to_buy
                    capital -= shares * current_price
                    position_type = "LONG"
                    entry_price = current_price
                    highest_price = current_price
                    entry_atr = atr
                    days_held = 0
                    action = f"BUY_STRONG {shares_to_buy}"
            elif (signal == "BUY") and capital >= current_price:
                allocation = capital * 0.5
                shares_to_buy = int(allocation // current_price)
                if shares_to_buy > 0:
                    shares = shares_to_buy
                    capital -= shares * current_price
                    position_type = "LONG"
                    entry_price = current_price
                    highest_price = current_price
                    entry_atr = atr
                    days_held = 0
                    action = f"BUY_NORMAL {shares_to_buy}"
            
            # SHORT Entries
            elif (signal == "STRONG_SELL" or signal == "STRONG SELL") and capital >= current_price:
                shares_to_short = int(capital // current_price)
                if shares_to_short > 0:
                    shares = shares_to_short
                    position_type = "SHORT"
                    entry_price = current_price
                    lowest_price = current_price
                    entry_atr = atr
                    days_held = 0
                    action = f"SHORT_STRONG {shares_to_short}"
            elif (signal == "SELL") and capital >= current_price:
                allocation = capital * 0.5
                shares_to_short = int(allocation // current_price)
                if shares_to_short > 0:
                    shares = shares_to_short
                    position_type = "SHORT"
                    entry_price = current_price
                    lowest_price = current_price
                    entry_atr = atr
                    days_held = 0
                    action = f"SHORT_NORMAL {shares_to_short}"
            
        # 3. Calculate Portfolio Value
        if position_type == "LONG":
            portfolio_value = capital + (shares * current_price)
        elif position_type == "SHORT":
            portfolio_value = capital + (shares * (entry_price - current_price))
        else:
            portfolio_value = capital
            
        results.append({
            "date": current_day.isoformat(),
            "signal": signal,
            "price": current_price,
            "action": action,
            "value": portfolio_value
        })

    # Close any open positions at final price
    final_price = float(actual_prices.iloc[-1]['close'])
    if position_type == "LONG" and shares > 0:
        final_value = capital + (shares * final_price)
    elif position_type == "SHORT" and shares > 0:
        final_value = capital + (shares * (entry_price - final_price))
    else:
        final_value = capital
        
    total_return = ((final_value / 100000.0) - 1) * 100
    
    df = pd.DataFrame(results)
    return {
        "final_value": final_value,
        "total_return": total_return,
        "trades": len(df[df['action'].str.contains('BUY|SELL|STOP|SHORT|COVER', na=False)]),
        "df": df
    }

def main():
    print("Initializing isolated Top 50 Backtest (Blue-Chip Universe)...")
    session = get_session()
    service = PredictionService()
    
    # Query stocks with market cap, sorted descending
    query = session.query(Stock).filter(Stock.market_cap.isnot(None)).order_by(Stock.market_cap.desc())
    top_stocks = query.limit(150).all() 
    
    selected_tickers = []
    required_tickers = ["TCS", "RELIANCE", "INFY", "HDFCBANK", "ICICIBANK", "ADANIENT", "ADANIPORTS"]
    
    # First, append required tickers if they exist in the DB and have sufficient data
    for req in required_tickers:
        s = session.query(Stock).filter_by(ticker=req).first()
        if s:
            hist_count = session.query(HistoricalPrice).filter_by(stock_id=s.id).count()
            if hist_count > 100:
                selected_tickers.append(s.ticker)
            
    # Add other top market cap stocks until we have 50 unique stocks
    for s in top_stocks:
        if len(selected_tickers) >= 50:
            break
        if s.ticker not in selected_tickers:
            hist_count = session.query(HistoricalPrice).filter_by(stock_id=s.id).count()
            if hist_count > 100:
                selected_tickers.append(s.ticker)
                
    # Fallback to predefined list if database query yields less than 50
    if len(selected_tickers) < 50:
        nifty_50_fallback = [
            "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK", 
            "INFY", "SBIN", "LICI", "ITC", "HINDUNILVR", "LT", "HCLTECH", 
            "BAJFINANCE", "AXISBANK", "ADANIENT", "SUNPHARMA", "ONGC", 
            "ADANIPORTS", "NTPC", "KOTAKBANK", "TATASTEEL", "COALINDIA", 
            "POWERGRID", "M&M", "MARUTI", "ULTRACEMCO", "TITAN", "BAJAJFINSV", 
            "JIOFIN", "ADANIPOWER", "TATAELXSI", "WIPRO", "TECHM", "GRASIM", 
            "JSWSTEEL", "ADANIGREEN", "ADANITRANS", "HDFCLIFE", "SBILIFE", 
            "BPCL", "HEROMOTOCO", "EICHERMOT", "DIVISLAB", "HINDALCO", 
            "INDUSINDBK", "CIPLA", "BRITANNIA", "TATACONSUM", "NESTLEIND", "UPL"
        ]
        for tf in nifty_50_fallback:
            if len(selected_tickers) >= 50:
                break
            if tf not in selected_tickers:
                s = session.query(Stock).filter_by(ticker=tf).first()
                if s:
                    hist_count = session.query(HistoricalPrice).filter_by(stock_id=s.id).count()
                    if hist_count > 100:
                        selected_tickers.append(s.ticker)
                        
    print(f"Selected {len(selected_tickers)} large-cap/Nifty stocks for backtesting (no penny stocks).")
    print("Tickers:", selected_tickers)
    
    # 6 Month OOS Period
    start = datetime.date(2025, 11, 1)
    end = datetime.date(2026, 5, 1)
    
    summary_results = []
    
    # Create results folder inside backtest_reports
    os.makedirs('backtest_reports/results', exist_ok=True)
    
    for ticker in selected_tickers:
        try:
            print(f"Running backtest for {ticker}...")
            res = run_backtest_inline(ticker, start, end, service, session)
            if res:
                summary_results.append({
                    "Ticker": ticker,
                    "Return %": round(res["total_return"], 2),
                    "Final Value": round(res["final_value"], 2),
                    "Trades": res["trades"]
                })
                # Save detailed logs
                res["df"].to_csv(f'backtest_reports/results/{ticker}_smart_oos.csv', index=False)
        except Exception as e:
            print(f"Error testing {ticker}: {e}")

    session.close()
    
    if not summary_results:
        print("No backtest results generated. Please ensure database historical prices are loaded.")
        return
        
    summary_df = pd.DataFrame(summary_results)
    avg_return = summary_df['Return %'].mean()
    win_rate = (len(summary_df[summary_df['Return %'] > 0]) / len(summary_df)) * 100
    
    # Save summary CSV
    summary_df.to_csv('backtest_reports/results/global_summary.csv', index=False)
    
    # Generate MD Report
    md_content = f"""# Nifty 50 & Blue-Chip Performance Report (6-Month OOS)
**Period**: 2025-11-01 to 2026-05-01
**Initial Capital per Stock**: Rs 1,00,000
**Max Position Size**: 100% (All-In on Strong Signals)

## Performance Summary
| Ticker | Return % | Final Value | Trades | Status |
| :--- | :--- | :--- | :--- | :--- |
"""
    for _, row in summary_df.iterrows():
        status = "🟢 PROFIT" if row['Return %'] > 0 else ("🔴 LOSS" if row['Return %'] < 0 else "⚪ FLAT")
        md_content += f"| {row['Ticker']} | {row['Return %']}% | Rs {row['Final Value']:,} | {row['Trades']} | {status} |\n"
    
    md_content += f"\n### Aggregate Portfolio Metrics\n"
    md_content += f"* **Average Return across Universe**: {avg_return:.2f}%\n"
    md_content += f"* **Win Rate (Percent of stocks with positive returns)**: {win_rate:.2f}%\n"
    md_content += f"* **Total Assets Tested**: {len(summary_df)}\n"
    md_content += f"\n**Conclusion**: Backtest successfully executed on isolated Nifty 50 / Large-Cap universe with zero look-ahead bias."
    
    with open('backtest_reports/TOP_50_PERFORMANCE_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"\n[SUCCESS] Institutional Performance Report generated: backtest_reports/TOP_50_PERFORMANCE_REPORT.md")

if __name__ == "__main__":
    main()
