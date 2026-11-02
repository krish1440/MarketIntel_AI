import time
import json
import logging
from datetime import datetime, date, timedelta, time as dtime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.config.settings import settings
from src.master.security_master import SecurityMaster
from src.crawler.daily_sync import DailySyncer
from src.crawler.intraday_gap_syncer import IntradayGapSyncer
from src.features.polars_engine import PolarsFeatureEngine

logger = logging.getLogger("GapOrchestrator")

IST = timezone(timedelta(hours=5, minutes=30))

class GapOrchestrator:
    """
    Unified Institutional Gap Orchestrator:
    - Scans both 1D and 1M data on disk for missing trading days.
    - Backfills 1D data to Silver and recomputes Gold feature stores.
    - Backfills 1M intraday candles from Angel One SmartAPI into Silver Parquet.
    - Capable of running sequentially (off-market) or as a non-blocking background thread (market open).
    """

    def __init__(self, exchange: str = "NSE"):
        self.exchange = exchange
        self.daily_syncer = DailySyncer(exchange=exchange)
        self.intraday_syncer = IntradayGapSyncer(exchange=exchange)
        self.feature_engine = PolarsFeatureEngine()
        self.is_running = False

    def get_full_universe(self) -> List[str]:
        """Loads the entire universe of all 2,357 NSE/BSE listed equities."""
        sec_master = SecurityMaster()
        if sec_master.df is not None:
            return sec_master.df["nse_symbol"].drop_nulls().to_list()
        return []

    def get_target_universe(self, limit: int = 300) -> List[str]:
        """Loads dynamically computed Top institutional turnover universe."""
        top_300_file = settings.DATA_DIR / "lakehouse" / "top_300_turnover_symbols.json"
        if top_300_file.exists():
            try:
                with open(top_300_file) as f:
                    symbols = json.load(f).get("symbols", [])
                    if symbols:
                        return symbols[:limit]
            except Exception as e:
                logger.warning(f"Could not read top 300 symbols: {e}")

        sec_master = SecurityMaster()
        if sec_master.df is not None:
            return sec_master.df["nse_symbol"].drop_nulls().to_list()[:limit]
        return ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "BHARTIARTL", "LT", "ICICIBANK", "ITC", "KOTAKBANK"]

    def refresh_top_universe_ranking(self) -> List[str]:
        """
        Dynamically recalculates the Top 300 Universe using institutional rules:
        - Price >= Rs.30.00 (Penny Stock & Pump-and-Dump Protection)
        - 20-Day Average Rolling Turnover >= Rs.2.0 Crores/day (High Liquidity)
        - Stocks are dynamically ranked descending by volume * price.
        """
        logger.info("[UNIVERSE RE-RANKING] Recalculating Top Turnover Leaders using Institutional Rules...")
        top_300_file = settings.DATA_DIR / "lakehouse" / "top_300_turnover_symbols.json"
        gold_m0_files = list(self.feature_engine.gold_model0_dir.glob("*.parquet"))
        sym_turnovers = []

        for f in gold_m0_files:
            try:
                import polars as pl
                tail_df = pl.scan_parquet(f).select(["symbol", "close", "turnover_20d_avg"]).tail(1).collect()
                if len(tail_df) > 0:
                    px = float(tail_df["close"].item(0) or 0)
                    to = float(tail_df["turnover_20d_avg"].item(0) or 0)
                    s = str(tail_df["symbol"].item(0))
                    if px >= 30.0 and to >= 2e7:  # Price >= Rs.30, Turnover >= 2 Cr
                        sym_turnovers.append((s, to, px))
            except Exception:
                pass

        sym_turnovers.sort(key=lambda x: x[1], reverse=True)
        top_300 = [s[0] for s in sym_turnovers[:300]]

        if top_300:
            with open(top_300_file, "w") as f:
                json.dump({
                    "symbols": top_300,
                    "count": len(top_300),
                    "min_price": 30.0,
                    "min_turnover_cr": 2.0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            logger.info(f"[UNIVERSE RE-RANKING] Dynamic list refreshed: {len(top_300)} liquid leaders saved to {top_300_file.name}.")
            return top_300
        return []

    def sync_1d_gaps(self, symbols: List[str], max_workers: int = 16) -> Tuple[int, int]:
        """
        Synchronizes missing 1D daily candles across all target symbols.
        Returns: (updated_symbols_count, up_to_date_symbols_count)
        """
        logger.info(f"[1D GAP SYNC] Checking Daily (1D) candles across {len(symbols)} symbols...")
        t0 = time.time()
        updated, up_to_date = self.daily_syncer.sync_bulk(symbols, max_workers=max_workers)
        logger.info(f"[1D GAP SYNC] Finished in {time.time() - t0:.1f}s | Updated: {updated} | Up-to-Date: {up_to_date}")

        # If any symbols were updated, refresh Gold features for those symbols
        if updated > 0:
            logger.info(f"[GOLD FEATURE REFRESH] Recalculating Gold features for {updated} updated symbols...")
            t_gold = time.time()
            exchange_dir = self.feature_engine.silver_ohlcv_dir / f"exchange={self.exchange}"
            for sym in symbols:
                target_file = exchange_dir / f"symbol={sym}" / "data.parquet"
                if target_file.exists():
                    try:
                        import polars as pl
                        df = pl.read_parquet(target_file)
                        if len(df) >= 30:
                            self.feature_engine.process_symbol(df, sym, self.exchange)
                    except Exception as e:
                        logger.warning(f"Failed to refresh gold features for {sym}: {e}")
            logger.info(f"[GOLD FEATURE REFRESH] Gold features refreshed in {time.time() - t_gold:.1f}s.")

        return updated, up_to_date

    def sync_1m_gaps(self, symbols: List[str], max_symbols: int = 50) -> int:
        """
        Synchronizes missing 1-minute intraday candles from Angel One SmartAPI.
        Prioritizes the highest-turnover symbols (first max_symbols).
        Returns: number of symbols updated with new 1-minute bars.
        """
        logger.info(f"[1M GAP SYNC] Checking 1-Minute historical candles across Top {min(len(symbols), max_symbols)} symbols...")
        target_list = symbols[:max_symbols]
        updated_count = 0
        t0 = time.time()

        for idx, sym in enumerate(target_list, 1):
            try:
                sym_name, success, count, msg = self.intraday_syncer.sync_symbol(sym)
                if success and count > 0:
                    updated_count += 1
                    logger.info(f"  [{idx}/{len(target_list)}] {sym_name:<10} | +{count:5} 1m bars | {msg}")
                elif not success:
                    logger.debug(f"  [{idx}/{len(target_list)}] {sym_name:<10} | {msg}")
            except Exception as e:
                logger.warning(f"1M sync error on {sym}: {e}")

        logger.info(f"[1M GAP SYNC] Finished in {time.time() - t0:.1f}s | {updated_count}/{len(target_list)} symbols backfilled.")
        return updated_count

    def run_full_gap_sync(self, universe_mode: str = "all", max_1m_symbols: int = 50, is_background: bool = False):
        """
        Executes end-to-end 1D and 1M gap resolution:
        1. 1D Sync across ALL 2,357 stocks in the entire listed equity universe.
        2. Dynamically recalculates the Top Turnover Universe using institutional rules.
        3. 1M Intraday Sync across top liquidity leaders.
        """
        mode_str = "BACKGROUND DAEMON" if is_background else "SEQUENTIAL PRE-FLIGHT"
        logger.info("=" * 75)
        logger.info(f"STARTING DUAL-ENGINE GAP BACKFILL ({mode_str} | Mode: {universe_mode.upper()})")
        logger.info("=" * 75)

        self.is_running = True
        try:
            # Step 1: 1D Sync across ALL stocks
            all_symbols = self.get_full_universe() if universe_mode == "all" else self.get_target_universe(limit=300)
            logger.info(f"[STEP 1] Syncing Daily (1D) bars across {len(all_symbols)} stocks...")
            self.sync_1d_gaps(all_symbols, max_workers=16)

            # Step 2: Dynamically re-rank Top Universe using Institutional Turnover Rules
            logger.info("[STEP 2] Dynamically refreshing Top Turnover Universe based on 20-day liquidity...")
            top_symbols = self.refresh_top_universe_ranking()
            if not top_symbols:
                top_symbols = self.get_target_universe(limit=300)

            # Step 3: 1M Intraday Sync across top dynamic leaders
            logger.info(f"[STEP 3] Syncing 1-Minute historical bars for top {max_1m_symbols} dynamic leaders...")
            self.sync_1m_gaps(top_symbols, max_symbols=max_1m_symbols)

            logger.info("=" * 75)
            logger.info(f"DUAL-ENGINE GAP BACKFILL COMPLETED SUCCESSFULLY ({mode_str})")
            logger.info("=" * 75)
        except Exception as e:
            logger.error(f"Dual-Engine Gap Sync encountered error: {e}", exc_info=True)
        finally:
            self.is_running = False
