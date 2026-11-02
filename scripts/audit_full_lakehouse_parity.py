import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import polars as pl

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.config.settings import settings
from src.master.security_master import SecurityMaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LakehouseAuditor")

IST = timezone(timedelta(hours=5, minutes=30))

def audit_lakehouse():
    logger.info("=" * 80)
    logger.info("       MARKETINTEL FULL LAKEHOUSE AUDIT & PARITY VERIFICATION")
    logger.info(f"       Current Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
    logger.info("=" * 80)

    sec_master = SecurityMaster()
    total_master_stocks = len(sec_master.df) if sec_master.df is not None else 0
    logger.info(f"Official Securities Master Universe: {total_master_stocks:,} scrips.\n")

    # --------------------------------------------------------------------------
    # 1. SILVER 1D DAILY AUDIT
    # --------------------------------------------------------------------------
    silver_1d_base = settings.SILVER_DIR / "ohlcv_1d" / "exchange=NSE"
    stock_1d_dirs = list(silver_1d_base.glob("symbol=*"))
    logger.info("=" * 70)
    logger.info(f"1. SILVER 1D (DAILY) LAKEHOUSE AUDIT ({len(stock_1d_dirs):,} stocks on disk)")
    logger.info("=" * 70)

    today_str = "2026-11-02"
    today_count_1d = 0
    earlier_count_1d = 0
    sample_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "BHARTIARTL", "LT", "ICICIBANK", "ITC", "KOTAKBANK",
                      "TRENT", "BEL", "SUZLON", "ZOMATO", "HAL", "CIPLA", "MARUTI", "WIPRO", "SUNPHARMA", "AXISBANK"]

    logger.info("Checking sample of 20 institutional stocks for today's 1D date:")
    for sym in sample_symbols:
        p = silver_1d_base / f"symbol={sym}" / "data.parquet"
        if p.exists():
            try:
                df = pl.read_parquet(p, columns=["date"])
                max_d = str(df["date"].max())[:10]
                status = "CURRENT (TODAY)" if max_d == today_str else f"LAST: {max_d}"
                logger.info(f"  {sym:<12} | Total Daily Bars: {len(df):5} | Max Date: {max_d} | [{status}]")
            except Exception as e:
                logger.warning(f"  {sym:<12} | Error reading: {e}")

    # Broad scan across 200 random stocks to check today's parity percentage
    scan_limit = min(200, len(stock_1d_dirs))
    for sdir in stock_1d_dirs[:scan_limit]:
        p = sdir / "data.parquet"
        if p.exists():
            try:
                df = pl.read_parquet(p, columns=["date"])
                max_d = str(df["date"].max())[:10]
                if max_d == today_str:
                    today_count_1d += 1
                else:
                    earlier_count_1d += 1
            except:
                pass

    pct_today_1d = (today_count_1d / scan_limit) * 100 if scan_limit > 0 else 0
    logger.info(f"\n-> Broad Scan ({scan_limit} stocks): {today_count_1d}/{scan_limit} ({pct_today_1d:.1f}%) have today's ({today_str}) daily candle on disk.")

    # --------------------------------------------------------------------------
    # 2. SILVER 1-MINUTE (1M) & 5-MINUTE (5M) AUDIT
    # --------------------------------------------------------------------------
    silver_1m_base = settings.SILVER_DIR / "ohlcv_1m" / "exchange=NSE"
    silver_5m_base = settings.SILVER_DIR / "ohlcv_5m" / "exchange=NSE"
    stock_1m_dirs = list(silver_1m_base.glob("symbol=*"))
    stock_5m_dirs = list(silver_5m_base.glob("symbol=*"))

    logger.info("\n" + "=" * 70)
    logger.info(f"2. SILVER 1M & 5M INTRADAY AUDIT (1M: {len(stock_1m_dirs):,} stocks | 5M: {len(stock_5m_dirs):,} stocks)")
    logger.info("=" * 70)

    for sym in sample_symbols[:6]:
        p1m = silver_1m_base / f"symbol={sym}" / "data.parquet"
        p5m = silver_5m_base / f"symbol={sym}" / "data.parquet"
        
        info_1m = "MISSING"
        info_5m = "MISSING"
        
        if p1m.exists():
            try:
                df1m = pl.read_parquet(p1m, columns=["timestamp"])
                info_1m = f"{len(df1m):,} bars (Latest: {df1m['timestamp'].max()})"
            except Exception as e:
                info_1m = f"Error: {e}"
                
        if p5m.exists():
            try:
                df5m = pl.read_parquet(p5m, columns=["timestamp"])
                info_5m = f"{len(df5m):,} bars (Latest: {df5m['timestamp'].max()})"
            except Exception as e:
                info_5m = f"Error: {e}"

        logger.info(f"  {sym:<12} | 1M: {info_1m}")
        logger.info(f"  {' '*12} | 5M: {info_5m}\n")

    # --------------------------------------------------------------------------
    # 3. GOLD FEATURE STORES AUDIT (MODELS 0, 1, 2, 3, 4)
    # --------------------------------------------------------------------------
    logger.info("=" * 70)
    logger.info("3. GOLD FEATURE LAKESTORE AUDIT (MODELS 0 TO 4)")
    logger.info("=" * 70)
    gold_dirs = {
        "Model 0 (Screener)": settings.DATA_DIR / "lakehouse" / "gold" / "features_screener_ranking",
        "Model 1 (Positional)": settings.DATA_DIR / "lakehouse" / "gold" / "features_short_term_positional",
        "Model 2 (Compounding)": settings.DATA_DIR / "lakehouse" / "gold" / "features_long_term_swing",
        "Model 3 (Price Corridor)": settings.DATA_DIR / "lakehouse" / "gold" / "features_price_corridor",
        "Model 4 (Action Classifier)": settings.DATA_DIR / "lakehouse" / "gold" / "features_stock_action_classifier",
    }

    for name, gdir in gold_dirs.items():
        if gdir.exists():
            count = len(list(gdir.glob("*.parquet")))
            logger.info(f"  {name:<28}: {count:,} stock feature parquets materialized.")
        else:
            logger.warning(f"  {name:<28}: Directory missing at {gdir}")

    logger.info("\n" + "=" * 80)
    logger.info("                   LAKEHOUSE AUDIT COMPLETED")
    logger.info("=" * 80)

if __name__ == "__main__":
    audit_lakehouse()

