import logging
from typing import List, Set, Optional
from pathlib import Path
import polars as pl

from src.config.settings import settings
from src.api.dependencies import ServiceContainer

logger = logging.getLogger("FocusUniverseService")

# Core macro & benchmark anchors to guarantee broad market calibration
CORE_BENCHMARK_ANCHORS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", 
    "ITC", "LT", "SBIN", "BHARTIARTL", "KOTAKBANK"
]


class FocusUniverseService:
    """
    Dynamic Focus Universe Resolver.
    
    Dynamically identifies and merges:
    1. Daily AI Model 0 Screener Watchlist (top momentum & Calmar ranked candidates)
    2. Active Paper Trading Portfolio Positions (tick-by-tick risk & exit tracking)
    3. Core Benchmark Anchors (for market breadth and macro regime context)
    
    Eliminates all hardcoded static lists and adapts directly to daily market rotation.
    """

    def __init__(self, services: ServiceContainer):
        self.services = services

    def get_today_focus_symbols(self, watchlist_size: int = 40) -> List[str]:
        """
        Resolves the comprehensive focus stock universe for today's live trading session.
        Returns a deduplicated, uppercase list of NSE symbols.
        """
        focus_symbols: Set[str] = set()

        # 1. Core Macro & Benchmark Anchors
        for anchor in CORE_BENCHMARK_ANCHORS:
            focus_symbols.add(anchor.strip().upper())

        # 2. Active Portfolio Positions (High-Priority for trailing stop & target protection)
        try:
            active_positions = list(self.services.portfolio_manager.positions.keys())
            for pos_sym in active_positions:
                sym_clean = pos_sym.strip().upper()
                if sym_clean:
                    focus_symbols.add(sym_clean)
            if active_positions:
                logger.info(f"Included {len(active_positions)} active portfolio positions into live feed focus.")
        except Exception as e:
            logger.warning(f"Could not load active positions for focus universe: {e}")

        # 3. Model 0 AI Daily Screener Candidates
        try:
            runner = self.services.strategy_runner
            candidates = getattr(runner, "focus_watchlist", None) or []
            if not candidates:
                try:
                    from src.models.data_splitter import DataSplitter
                    splitter = DataSplitter()
                    _, test_df0 = splitter.load_dataset(0, max_symbols=300, min_turnover_cr=2.0)
                    latest_day = test_df0["date"].max()
                    day_df = test_df0.filter(pl.col("date") == latest_day)
                    candidates = runner.run_premarket_screener(day_df)
                except Exception as ex:
                    logger.debug(f"Pre-market screener preview failed: {ex}")

            added_candidates = 0
            for c in (candidates[:watchlist_size] if candidates else []):
                sym = getattr(c, "symbol", str(c)).strip().upper()
                if sym:
                    focus_symbols.add(sym)
                    added_candidates += 1
            logger.info(f"Loaded {added_candidates} AI Screener candidates into live feed focus.")
        except Exception as e:
            logger.warning(f"Model 0 dynamic screener query failed: {e}. Falling back to lakehouse liquidity ranking.")
            fallback_symbols = self._get_lakehouse_liquidity_fallback(limit=watchlist_size)
            for sym in fallback_symbols:
                focus_symbols.add(sym)

        # 4. Filter to ensure every symbol exists in Security Master
        valid_symbols: List[str] = []
        sec_master = self.services.security_master
        for sym in sorted(list(focus_symbols)):
            token = sec_master.get_token(sym)
            if token:
                valid_symbols.append(sym)
            else:
                logger.debug(f"Symbol {sym} has no token mapping in SecurityMaster; skipping.")

        logger.info(f"Dynamic Focus Universe resolved: {len(valid_symbols)} total equities for live streaming.")
        return valid_symbols

    def _get_lakehouse_liquidity_fallback(self, limit: int = 40) -> List[str]:
        """
        Fallback mechanism when Model 0 feature vectors are uncomputed:
        Queries Silver 1D OHLCV parquets and returns the top symbols by recent trading turnover.
        """
        symbols = []
        silver_dir = settings.SILVER_DIR / "ohlcv_1d" / "exchange=NSE"
        if not silver_dir.exists():
            return CORE_BENCHMARK_ANCHORS

        stock_turnovers = []
        for stock_folder in list(silver_dir.glob("symbol=*"))[:200]:
            sym = stock_folder.name.replace("symbol=", "").upper()
            parquet_file = stock_folder / "data.parquet"
            if parquet_file.exists():
                try:
                    df = pl.read_parquet(parquet_file)
                    if len(df) > 0 and "close" in df.columns and "volume" in df.columns:
                        last_row = df.tail(1)
                        turnover = float(last_row["close"].item(0)) * float(last_row["volume"].item(0))
                        stock_turnovers.append((sym, turnover))
                except Exception:
                    continue

        stock_turnovers.sort(key=lambda x: x[1], reverse=True)
        return [sym for sym, _ in stock_turnovers[:limit]]
