import sqlite3
import polars as pl
import numpy as np

conn = sqlite3.connect("data/paper_trading/vault_test/real_day_by_day_ledger.db")
cursor = conn.cursor()
cursor.execute("SELECT symbol, entry_time, exit_time, holding_days, quantity, entry_price, exit_price, gross_pnl, net_pnl, net_pnl_pct, exit_trigger FROM trade_history")
cols = ["symbol", "entry_time", "exit_time", "holding_days", "quantity", "entry_price", "exit_price", "gross_pnl", "net_pnl", "net_pnl_pct", "exit_trigger"]
rows = cursor.fetchall()
df = pl.DataFrame(rows, schema=cols, orient="row")

winners = df.filter(pl.col("net_pnl") > 0)
losers = df.filter(pl.col("net_pnl") < 0)

win_net_sum = winners["net_pnl"].sum()
loss_net_sum = losers["net_pnl"].sum()

print("=" * 70)
print("             DEEP TRADE METRICS & WIN/LOSS FORENSICS")
print("=" * 70)
print(f"Total Settled Legs: {len(df)}")
print(f"Winning Trades    : {len(winners)} ({len(winners)/len(df)*100:.1f}%) | Total Net: Rs.{win_net_sum:,.2f}")
print(f"Losing Trades     : {len(losers)} ({len(losers)/len(df)*100:.1f}%) | Total Net: Rs.{loss_net_sum:,.2f}")
print(f"Avg Winner Gain   : Rs.{winners['net_pnl'].mean():,.2f} ({winners['net_pnl_pct'].mean():.2f}%)")
print(f"Avg Loser Loss    : Rs.{losers['net_pnl'].mean():,.2f} ({losers['net_pnl_pct'].mean():.2f}%)")
print(f"Profit Factor     : {abs(win_net_sum / loss_net_sum):.2f}")
print(f"Reward-to-Risk    : {abs(winners['net_pnl'].mean() / losers['net_pnl'].mean()):.2f}x")

print("\n" + "=" * 70)
print("             PERFORMANCE BY EXIT TRIGGER")
print("=" * 70)
for trig in sorted(df["exit_trigger"].unique().to_list()):
    sub = df.filter(pl.col("exit_trigger") == trig)
    w_cnt = len(sub.filter(pl.col("net_pnl") > 0))
    print(f"{trig:<28}: Count={len(sub):>2} | WinRate={w_cnt/len(sub)*100:>5.1f}% | TotalGross=Rs.{sub['gross_pnl'].sum():>10.2f} | TotalNet=Rs.{sub['net_pnl'].sum():>10.2f} | AvgHold={sub['holding_days'].mean():.1f}d")

print("\n" + "=" * 70)
print("             CAPITAL ALLOCATION FORENSICS")
print("=" * 70)
# Check capital per trade
cursor.execute("SELECT quantity * entry_price FROM trade_history")
trade_caps = [r[0] for r in cursor.fetchall()]
print(f"Avg Capital per Trade Leg: Rs.{np.mean(trade_caps):,.2f}")
print(f"Max Capital per Trade Leg: Rs.{np.max(trade_caps):,.2f}")
print(f"Min Capital per Trade Leg: Rs.{np.min(trade_caps):,.2f}")

# Check position concentration & cash drag
cursor.execute("SELECT COUNT(DISTINCT symbol) FROM trade_history")
unique_syms = cursor.fetchone()[0]
print(f"Distinct Symbols Traded  : {unique_syms}")

print("\n" + "=" * 70)
print("             LARGEST 5 LOSING TRADES")
print("=" * 70)
for row in losers.sort("net_pnl").head(5).iter_rows(named=True):
    print(f"Symbol: {row['symbol']:<10} | Loss: Rs.{row['net_pnl']:>9,.2f} ({row['net_pnl_pct']:>6.2f}%) | Hold: {row['holding_days']:>3}d | Entry: Rs.{row['entry_price']:.2f} -> Exit: Rs.{row['exit_price']:.2f} | Trigger: {row['exit_trigger']}")

print("\n" + "=" * 70)
print("             LARGEST 5 WINNING TRADES")
print("=" * 70)
for row in winners.sort("net_pnl", descending=True).head(5).iter_rows(named=True):
    print(f"Symbol: {row['symbol']:<10} | Gain: Rs.{row['net_pnl']:>9,.2f} ({row['net_pnl_pct']:>6.2f}%) | Hold: {row['holding_days']:>3}d | Entry: Rs.{row['entry_price']:.2f} -> Exit: Rs.{row['exit_price']:.2f} | Trigger: {row['exit_trigger']}")

