import sqlite3
import json

conn = sqlite3.connect("data/paper_trading/vault_test/real_day_by_day_ledger.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM orders")
order_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM trade_history")
trade_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT symbol) FROM trade_history")
unique_symbols = cursor.fetchone()[0]

print("================================================================================")
print("             DEEP VERIFICATION OF SIMULATED TRADE LEDGER")
print("================================================================================")
print(f"Total Orders Filled        : {order_count}")
print(f"Total Settled Trade Records: {trade_count}")
print(f"Distinct Stocks Traded     : {unique_symbols}")

# Monthly distribution of entries
cursor.execute("""
    SELECT SUBSTR(entry_time, 1, 7) as ym, COUNT(*), SUM(gross_pnl), SUM(net_pnl)
    FROM trade_history
    GROUP BY ym
    ORDER BY ym
""")
print("\n--- MONTHLY TRADE & PROFIT DISTRIBUTION ---")
monthly = cursor.fetchall()
for ym, cnt, gross, net in monthly:
    print(f"  {ym}: {cnt:>3} trades | Gross: Rs.{gross:>+10,.2f} | Net: Rs.{net:>+10,.2f}")

print("\n--- SAMPLE WINNING TRADES (How they bought and where they sold) ---")
cursor.execute("""
    SELECT symbol, entry_time, exit_time, holding_days, quantity, entry_price, exit_price, gross_pnl, net_pnl, net_pnl_pct, exit_trigger
    FROM trade_history
    WHERE net_pnl > 5000
    ORDER BY net_pnl DESC
    LIMIT 6
""")
for row in cursor.fetchall():
    sym, en_t, ex_t, hold, qty, en_p, ex_p, g_pnl, n_pnl, n_pct, trig = row
    print(f"  Stock: {sym:<10} | Bought: {en_t[:10]} @ Rs.{en_p:.2f} (Qty: {qty}) | Sold: {ex_t[:10]} @ Rs.{ex_p:.2f} | Hold: {hold}d")
    print(f"    -> Net Gain: Rs.{n_pnl:>+8,.2f} ({n_pct:>+6.2f}%) | Trigger: {trig}")
    print()

print("--- SAMPLE DEFENSIVE LOSS TRADES (Controlled stop-outs) ---")
cursor.execute("""
    SELECT symbol, entry_time, exit_time, holding_days, quantity, entry_price, exit_price, gross_pnl, net_pnl, net_pnl_pct, exit_trigger
    FROM trade_history
    WHERE net_pnl < -5000
    ORDER BY net_pnl ASC
    LIMIT 5
""")
for row in cursor.fetchall():
    sym, en_t, ex_t, hold, qty, en_p, ex_p, g_pnl, n_pnl, n_pct, trig = row
    print(f"  Stock: {sym:<10} | Bought: {en_t[:10]} @ Rs.{en_p:.2f} (Qty: {qty}) | Sold: {ex_t[:10]} @ Rs.{ex_p:.2f} | Hold: {hold}d")
    print(f"    -> Net Loss: Rs.{n_pnl:>+8,.2f} ({n_pct:>+6.2f}%) | Trigger: {trig}")
    print()

# Check buying rule in simulation:
# Check how many stocks were considered each day
print("--- PORTFOLIO UTILIZATION & CASH FORENSICS ---")
cursor.execute("SELECT MIN(holding_days), AVG(holding_days), MAX(holding_days) FROM trade_history")
min_h, avg_h, max_h = cursor.fetchone()
print(f"Holding Time: Min={min_h:.1f}d, Avg={avg_h:.1f}d, Max={max_h:.1f}d")

