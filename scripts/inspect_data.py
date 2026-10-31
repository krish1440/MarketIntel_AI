import sys
from pathlib import Path
import polars as pl

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def inspect():
    # 1. Master Security Table
    master_path = Path("data/lakehouse/bronze/master/securities_master.parquet")
    print("=" * 70)
    print("1. MASTER SECURITIES TABLE (Bronze)")
    print("=" * 70)
    if master_path.exists():
        df_master = pl.read_parquet(master_path)
        print(f"Total Securities Indexed: {len(df_master)}")
        print(f"File Size: {master_path.stat().st_size / 1024:.2f} KB\n")
        print("Sample Records:")
        print(df_master.select(["isin", "nse_symbol", "nse_token", "bse_code", "company_name"]).head(5))
    else:
        print("Master file does not exist!")

    # 2. Daily Stocks (RELIANCE & TCS)
    print("\n" + "=" * 70)
    print("2. HISTORICAL DAILY OHLCV BARS (Silver Layer)")
    print("=" * 70)
    for sym in ["RELIANCE", "TCS"]:
        p = Path(f"data/lakehouse/silver/ohlcv_1d/exchange=NSE/symbol={sym}/data.parquet")
        if p.exists():
            df = pl.read_parquet(p)
            print(f"\n--- Symbol: {sym} ---")
            print(f"Total Candles: {len(df)}")
            print(f"Date Range: {df['date'].min()} --> {df['date'].max()}")
            print(f"Latest 5 Candles:")
            print(df.tail(5))
        else:
            print(f"No data file for {sym}")

if __name__ == "__main__":
    inspect()

