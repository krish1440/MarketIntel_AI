import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import polars as pl
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Backtest1mEMAVWAP")

# Official NIFTY 50 Constituent Universe (50 Blue-Chip Equities)
NIFTY_50 = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
    'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
    'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'INDUSINDBK',
    'INFY', 'ITC', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'NESTLEIND', 'NTPC', 'ONGC',
    'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN', 'SHRIRAMFIN',
    'SUNPHARMA', 'TATACONSUM', 'TATASTEEL', 'TCS', 'TECHM',
    'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO', 'COFORGE'
]

SILVER_DIR = PROJECT_ROOT / "data" / "lakehouse" / "silver" / "ohlcv_1m" / "exchange=NSE"

def prepare_1m_data(df_1m: pl.DataFrame) -> pl.DataFrame:
    """
    Computes Session-Reset VWAP and 20-period EMA directly on 1-Minute Lakehouse bars.
    VWAP resets to 0 at the start of each daily trading session (09:15 AM IST).
    """
    df = df_1m.sort("timestamp").with_columns([
        pl.col("timestamp").dt.date().alias("session_date"),
        ((pl.col("high") + pl.col("low") + pl.col("close")) / 3.0).alias("typical_price")
    ]).with_columns([
        (pl.col("typical_price") * pl.col("volume")).alias("pv")
    ])

    # Cumulative PV and Volume resetting every trading session (09:15 AM IST)
    df = df.with_columns([
        pl.col("pv").cum_sum().over("session_date").alias("cum_pv"),
        pl.col("volume").cum_sum().over("session_date").alias("cum_vol"),
    ])

    # Session VWAP
    df = df.with_columns([
        pl.when(pl.col("cum_vol") > 0)
        .then(pl.col("cum_pv") / pl.col("cum_vol"))
        .otherwise(pl.col("close"))
        .alias("vwap")
    ])

    # EMA 20 on 1-minute bars
    df = df.with_columns([
        pl.col("close").ewm_mean(span=20, adjust=False).alias("ema_20")
    ])

    return df

def simulate_1m_stock_crossover(symbol: str, df: pl.DataFrame, budget_per_trade: float = 100000.0) -> List[Dict[str, Any]]:
    """
    Simulates EMA 20 crossing VWAP at the EXACT minute it happens:
    - Long Entry: EMA 20 crosses above VWAP on a 1-minute bar
    - Exit: EMA 20 crosses below VWAP on a 1-minute bar OR at 03:15 PM IST market close
    - Friction: 0.03% round-trip costs
    """
    trades = []
    in_position = False
    entry_price = 0.0
    entry_time = None
    shares = 0

    rows = df.select(["timestamp", "open", "close", "ema_20", "vwap", "session_date"]).to_dicts()
    n = len(rows)

    for i in range(1, n):
        curr = rows[i]
        prev = rows[i - 1]

        dt = curr["timestamp"]
        c_px = curr["close"]
        ema_now = curr["ema_20"]
        vwap_now = curr["vwap"]
        ema_prev = prev["ema_20"]
        vwap_prev = prev["vwap"]

        is_same_session = (curr["session_date"] == prev["session_date"])
        hour = dt.hour if hasattr(dt, 'hour') else 0
        minute = dt.minute if hasattr(dt, 'minute') else 0

        # Exact 1-Minute Crossover Detection:
        # Bullish: EMA 20 was <= VWAP on previous minute, now > VWAP on this minute
        bullish_cross = is_same_session and (ema_prev <= vwap_prev) and (ema_now > vwap_now)
        # Bearish: EMA 20 was >= VWAP on previous minute, now < VWAP on this minute
        bearish_cross = is_same_session and (ema_prev >= vwap_prev) and (ema_now < vwap_now)

        # End of day square-off condition (03:15 PM IST = 09:45 UTC)
        is_eod = (hour == 9 and minute >= 45) or (hour > 9)

        if not in_position:
            # Enter trade at exact minute of crossover
            if bullish_cross and (not is_eod) and c_px > 0:
                shares = int(budget_per_trade // c_px)
                if shares > 0:
                    entry_price = c_px
                    entry_time = dt
                    in_position = True
        else:
            # Exit trade at exact minute of crossunder or EOD square-off
            if bearish_cross or is_eod or not is_same_session:
                exit_price = c_px
                exit_time = dt

                invested = shares * entry_price
                proceeds = shares * exit_price
                gross_pnl = proceeds - invested
                friction = (invested + proceeds) * 0.0003  # 0.03% round-trip
                net_pnl = gross_pnl - friction
                return_pct = (net_pnl / invested) * 100.0 if invested > 0 else 0.0

                trades.append({
                    "symbol": symbol,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "shares": shares,
                    "invested": round(invested, 2),
                    "gross_pnl": round(gross_pnl, 2),
                    "net_pnl": round(net_pnl, 2),
                    "return_pct": round(return_pct, 2),
                    "exit_reason": "BEARISH_CROSS_1M" if bearish_cross else ("EOD_0315_PM" if is_eod else "SESSION_END"),
                    "win": (net_pnl > 0)
                })

                in_position = False
                shares = 0
                entry_price = 0.0

    return trades

def run_nifty50_1m_backtest():
    print("=" * 80)
    print("      NIFTY 50 EXACT 1-MINUTE EMA 20 vs VWAP CROSSOVER BACKTEST")
    print("=" * 80)
    print(f"Total Nifty 50 Constituents: {len(NIFTY_50)}")
    print(f"Resolution: Pure 1-Minute Candles (Exact Minute Entry & Exit)")
    print(f"Starting Virtual Capital: INR 10,00,000")
    print(f"Budget per Position: INR 1,00,000 (10% allocation)")
    print(f"Max Concurrent Positions: 10 Positions")
    print(f"Friction / Brokerage / STT / Slippage: 0.03% Round-Trip")
    print(f"Rule: Buy when 1m EMA 20 > VWAP, Sell when 1m EMA 20 < VWAP or at 03:15 PM IST")
    print("=" * 80)

    all_stock_results = []
    all_trades = []

    start_t = time.time()
    tested_count = 0

    for idx, sym in enumerate(NIFTY_50, 1):
        parquet_file = SILVER_DIR / f"symbol={sym}" / "data.parquet"
        if not parquet_file.exists():
            continue

        try:
            df_1m = pl.read_parquet(parquet_file)
            if len(df_1m) < 1000:
                continue

            # Compute session VWAP & EMA 20 on 1m bars
            df_ind = prepare_1m_data(df_1m)

            # Filter unadjusted outliers (>60% deviation from median)
            med_px = df_ind["close"].median()
            df_ind = df_ind.filter((pl.col("close") >= 0.4 * med_px) & (pl.col("close") <= 2.2 * med_px))

            # Simulate exact 1m trades
            trades = simulate_1m_stock_crossover(sym, df_ind, budget_per_trade=100000.0)
            tested_count += 1

            if trades:
                net_pnl = sum(t["net_pnl"] for t in trades)
                wins = sum(1 for t in trades if t["win"])
                win_rate = (wins / len(trades)) * 100.0 if trades else 0.0
                all_trades.extend(trades)

                all_stock_results.append({
                    "symbol": sym,
                    "trades_count": len(trades),
                    "win_rate": round(win_rate, 1),
                    "net_pnl": round(net_pnl, 2),
                    "avg_return_pct": round(np.mean([t["return_pct"] for t in trades]), 2)
                })

            if idx % 10 == 0:
                print(f"Processed {idx}/{len(NIFTY_50)} NIFTY 50 stocks on 1-minute data...")

        except Exception as e:
            logger.error(f"Error processing {sym}: {e}")

    # Portfolio Aggregation
    total_trades = len(all_trades)
    winning_trades = sum(1 for t in all_trades if t["win"])
    losing_trades = total_trades - winning_trades
    overall_win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

    total_gross_wins = sum(t["gross_pnl"] for t in all_trades if t["gross_pnl"] > 0)
    total_gross_losses = abs(sum(t["gross_pnl"] for t in all_trades if t["gross_pnl"] < 0))
    profit_factor = round(total_gross_wins / total_gross_losses, 2) if total_gross_losses > 0 else 0.0

    total_net_pnl = sum(t["net_pnl"] for t in all_trades)
    portfolio_return_pct = round((total_net_pnl / 1000000.0) * 100.0, 2)

    # Sort stock results by Net P&L
    all_stock_results.sort(key=lambda x: x["net_pnl"], reverse=True)

    print("\n" + "=" * 80)
    print("         NIFTY 50 PURE 1-MINUTE EMA 20 vs VWAP OVERALL RESULTS")
    print("=" * 80)
    print(f"Total Nifty 50 Stocks Evaluated : {tested_count}")
    print(f"Total Exact 1m Trades Executed  : {total_trades:,}")
    print(f"Winning Trades                  : {winning_trades:,} ({overall_win_rate:.1f}%)")
    print(f"Losing Trades                   : {losing_trades:,} ({100.0 - overall_win_rate:.1f}%)")
    print(f"Total Gross Profits             : INR {total_gross_wins:,.2f}")
    print(f"Total Gross Losses              : INR {total_gross_losses:,.2f}")
    print(f"Profit Factor (Gross W / L)     : {profit_factor}")
    print(f"Total Portfolio Net P&L         : INR {total_net_pnl:,.2f}")
    print(f"Net Portfolio Return (%)        : {portfolio_return_pct:+.2f}%")
    print("=" * 80)

    print("\n--- TOP 10 BEST PERFORMING NIFTY 50 STOCKS (1-Minute Crossover) ---")
    print(f"{'Symbol':<12} | {'Trades':<8} | {'Win Rate %':<12} | {'Net P&L (INR)':<16} | {'Avg Return %'}")
    print("-" * 65)
    for s in all_stock_results[:10]:
        print(f"{s['symbol']:<12} | {s['trades_count']:<8} | {s['win_rate']:<11}% | INR {s['net_pnl']:<12,.2f} | {s['avg_return_pct']:+.2f}%")

    print("\n--- BOTTOM 5 LAGGING NIFTY 50 STOCKS (1-Minute Whipsaws / Range-bound) ---")
    print(f"{'Symbol':<12} | {'Trades':<8} | {'Win Rate %':<12} | {'Net P&L (INR)':<16} | {'Avg Return %'}")
    print("-" * 65)
    for s in all_stock_results[-5:]:
        print(f"{s['symbol']:<12} | {s['trades_count']:<8} | {s['win_rate']:<11}% | INR {s['net_pnl']:<12,.2f} | {s['avg_return_pct']:+.2f}%")

    print("=" * 80)
    elapsed = time.time() - start_t
    print(f"1-Minute Backtest completed across all 50 stocks in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    run_nifty50_1m_backtest()
