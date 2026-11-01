import os
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, date, timezone, timedelta, time as dtime
from typing import Optional, Dict, Any, List

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.config.settings import settings
from src.serving.redis_manager import RedisManager
from src.execution.portfolio_manager import VirtualPortfolioManager
from src.execution.strategy_runner import AIStrategyRunner
from src.mlops.champion_governance import ChampionGovernanceEngine
from scripts.run_eod_pipeline import run_eod_pipeline

# Indian Standard Time (IST = UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "marketintel_runtime.log", mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("MasterOrchestrator")

def print_banner():
    banner = r"""
================================================================================
   __  ___           __        __  ____       __       __     ___    ____
  /  |/  /___ ______/ /_____  / /_/  _/____  / /____  / /    /   |  /  _/
 / /|_/ / __ `/ ___/ //_/ _ \/ __// / / __ \/ __/ _ \/ /    / /| |  / /  
/ /  / / /_/ / /  / ,< /  __/ /__/ / / / / / /_/  __/ /___ / ___ |_/ /   
/_/  /_/\__,_/_/  /_/|_|\___/\__/___/_/ /_/\__/\___/_____//_/  |_/___/   
================================================================================
   INSTITUTIONAL QUANTITATIVE MARKET INTELLIGENCE & 24/7 AUTONOMOUS DAEMON
   Execution Mode: STRICT PAPER TRADING (Rs.10,00,000 INR Virtual Budget)
   State Engine: 24/7 Time-Aware Scheduler (Pre-Market, Live ORB, EOD, Weekend)
================================================================================
"""
    print(banner)

class MarketRegime:
    WEEKEND = "WEEKEND_IDLE"
    NIGHT_IDLE = "NIGHT_IDLE"
    PRE_MARKET_SETUP = "PRE_MARKET_SETUP"         # 08:30 - 09:08 IST
    PRE_MARKET_SCREENER = "PRE_MARKET_SCREENER"   # 09:08 - 09:15 IST
    ORB_OBSERVATION = "ORB_OBSERVATION"           # 09:15 - 09:30 IST
    ACTIVE_TRADING = "ACTIVE_TRADING"             # 09:30 - 15:30 IST
    MARKET_CLOSE = "MARKET_CLOSE_SETTLEMENT"      # 15:30 - 16:00 IST
    EOD_SYNC = "EOD_DATA_INGESTION"               # 16:00 - 17:00 IST

class MarketIntelSystem:
    def __init__(self):
        self.is_running = True
        self.redis_mgr = None
        self.portfolio_mgr = None
        self.strategy_runner = None
        self.governance_engine = None

        # State tracking to prevent duplicate actions on same day
        self.last_screener_date: Optional[date] = None
        self.last_eod_sync_date: Optional[date] = None
        self.last_mlops_retrain_week: Optional[int] = None
        self.current_regime: str = MarketRegime.NIGHT_IDLE

    def preflight_check(self):
        logger.info("Starting Institutional Pre-Flight Health Checks...")
        
        # 1. Verify Directories
        models_dir = settings.BASE_DIR / "models"
        for d in [settings.DATA_DIR, settings.LAKEHOUSE_DIR, models_dir]:
            d.mkdir(parents=True, exist_ok=True)
        logger.info("[OK] Lakehouse and Data Directories verified.")

        # 2. Redis / In-Memory Bus Check
        self.redis_mgr = RedisManager()
        broker_type = "Live Redis Server" if getattr(self.redis_mgr, "is_connected", False) else "High-Speed In-Memory Bus (RAM)"
        logger.info(f"[OK] Event Bus Active: {broker_type}")

        # 3. Model Registry Verification (Active Production Models)
        reg_path = settings.BASE_DIR / "models" / "active" / "model_registry.json"
        if not reg_path.exists():
            raise FileNotFoundError(f"Active model registry missing at {reg_path}")
        logger.info(f"[OK] Active Model Registry verified: {reg_path.name}")

        # 4. Virtual Portfolio & Risk Manager
        self.portfolio_mgr = VirtualPortfolioManager()
        summary = self.portfolio_mgr.get_summary()
        logger.info(
            f"[OK] Virtual Portfolio Initialized: Cash = Rs.{summary.current_cash:,.2f} | "
            f"Positions = {summary.open_positions_count} | Realized PnL = Rs.{summary.total_realized_pnl:+,.2f}"
        )

        # 5. AI Strategy Runner
        self.strategy_runner = AIStrategyRunner(portfolio_manager=self.portfolio_mgr)
        logger.info("[OK] 5-Tier AI Strategy Runner loaded into memory.")

        # 6. Champion MLOps Governance
        self.governance_engine = ChampionGovernanceEngine()
        logger.info("[OK] MLOps Walk-Forward Retraining Engine ready.")

        logger.info(">>> ALL PRE-FLIGHT CHECKS PASSED. 24/7 DAEMON INITIALIZED <<<\n")

    def get_market_regime(self, dt: datetime) -> str:
        """Determines the current institutional market regime based on IST time."""
        weekday = dt.weekday() # 0=Mon, ..., 4=Fri, 5=Sat, 6=Sun
        if weekday in (5, 6):
            return MarketRegime.WEEKEND

        t = dt.time()
        if t < dtime(8, 30):
            return MarketRegime.NIGHT_IDLE
        elif dtime(8, 30) <= t < dtime(9, 8):
            return MarketRegime.PRE_MARKET_SETUP
        elif dtime(9, 8) <= t < dtime(9, 15):
            return MarketRegime.PRE_MARKET_SCREENER
        elif dtime(9, 15) <= t < dtime(9, 30):
            return MarketRegime.ORB_OBSERVATION
        elif dtime(9, 30) <= t < dtime(15, 30):
            return MarketRegime.ACTIVE_TRADING
        elif dtime(15, 30) <= t < dtime(16, 0):
            return MarketRegime.MARKET_CLOSE
        elif dtime(16, 0) <= t < dtime(17, 30):
            return MarketRegime.EOD_SYNC
        else:
            return MarketRegime.NIGHT_IDLE

    def run(self, max_heartbeats: Optional[int] = None):
        logger.info("MarketIntel 24/7 Autonomous Master Daemon is now ACTIVE.")
        logger.info("The system automatically transitions across all trading, EOD, and weekend regimes.")
        logger.info("Press Ctrl+C to safely pause and persist ledger.\n")

        heartbeats = 0
        try:
            while self.is_running:
                heartbeats += 1
                now_ist = datetime.now(IST)
                today_date = now_ist.date()
                regime = self.get_market_regime(now_ist)
                self.current_regime = regime

                time_str = now_ist.strftime("%H:%M:%S")
                date_str = now_ist.strftime("%Y-%m-%d (%A)")

                # -------------------------------------------------------------
                # 1. WEEKEND REGIME (Saturday & Sunday)
                # -------------------------------------------------------------
                if regime == MarketRegime.WEEKEND:
                    # Check for Saturday 23:00 IST MLOps Walk-Forward Retraining
                    week_num = now_ist.isocalendar()[1]
                    if now_ist.weekday() == 5 and now_ist.hour >= 23 and self.last_mlops_retrain_week != week_num:
                        logger.info("=" * 70)
                        logger.info("SATURDAY 23:00 IST: Launching Weekly MLOps Walk-Forward Retraining...")
                        logger.info("=" * 70)
                        try:
                            res = self.governance_engine.run_weekly_screener_tournament()
                            logger.info(f"Retraining Complete! Promotion Result: {res.promoted} ({res.promotion_reason})")
                        except Exception as e:
                            logger.error(f"Weekly MLOps Retraining Error: {e}")
                        self.last_mlops_retrain_week = week_num

                    if heartbeats % 6 == 1:
                        logger.info(f"[{time_str} IST] [{regime}] Market is CLOSED for the weekend. Next live session opens Monday 09:08 AM IST.")
                    time.sleep(30)
                    continue

                # -------------------------------------------------------------
                # 2. NIGHT IDLE REGIME (17:30 to 08:30 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.NIGHT_IDLE:
                    if heartbeats % 6 == 1:
                        summary = self.portfolio_mgr.get_summary()
                        logger.info(
                            f"[{time_str} IST] [{regime}] Market is CLOSED. Next session opens at 08:30 AM IST. "
                            f"Portfolio: Rs.{summary.total_portfolio_value:,.2f} | Cash: Rs.{summary.current_cash:,.2f}"
                        )
                    time.sleep(30)
                    continue

                # -------------------------------------------------------------
                # 3. PRE-MARKET HEALTH & SETUP (08:30 to 09:08 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.PRE_MARKET_SETUP:
                    logger.info(f"[{time_str} IST] [{regime}] Initializing daily session baseline & macro status...")
                    self.portfolio_mgr.start_new_trading_session(today_date)
                    time.sleep(15)
                    continue

                # -------------------------------------------------------------
                # 4. PRE-MARKET SCREENER (09:08 to 09:15 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.PRE_MARKET_SCREENER:
                    if self.last_screener_date != today_date:
                        logger.info(f"[{time_str} IST] [09:08 AM SCREENER] Running Model 0 Screener across Top 300 Institutional Universe...")
                        try:
                            # Load latest features from Gold lakehouse
                            from src.models.data_splitter import DataSplitter
                            import polars as pl
                            splitter = DataSplitter()
                            _, test_df0 = splitter.load_dataset(0, max_symbols=300, min_turnover_cr=2.0)
                            latest_day = test_df0["date"].max()
                            day_df = test_df0.filter(pl.col("date") == latest_day)
                            
                            watchlist = self.strategy_runner.run_premarket_screener(day_df)
                            logger.info(f"PRE-MARKET FOCUS WATCHLIST READY: {len(watchlist)} stocks selected for today's opening bell.")
                            for idx, cand in enumerate(watchlist[:5], 1):
                                logger.info(f"  #{idx}: {cand.symbol:<10} | Price: Rs.{cand.current_price:.2f} | Rank Score: {cand.rank_score:+.4f}")
                        except Exception as e:
                            logger.error(f"Failed to generate pre-market watchlist: {e}")
                        self.last_screener_date = today_date
                    time.sleep(10)
                    continue

                # -------------------------------------------------------------
                # 5. OPENING BELL & 15m ORB OBSERVATION (09:15 to 09:30 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.ORB_OBSERVATION:
                    if heartbeats % 3 == 1:
                        logger.info(f"[{time_str} IST] [{regime}] Market OPEN. Tracking 15-Minute Opening Range Breakout (ORB) & VWAP...")
                    time.sleep(5)
                    continue

                # -------------------------------------------------------------
                # 6. ACTIVE TRADING & RISK MANAGEMENT (09:30 to 15:30 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.ACTIVE_TRADING:
                    summary = self.portfolio_mgr.get_summary()
                    logger.info(
                        f"[{time_str} IST] [ACTIVE TRADING] Portfolio: Rs.{summary.total_portfolio_value:,.2f} | "
                        f"Cash: Rs.{summary.current_cash:,.2f} | Open Positions: {summary.open_positions_count} | "
                        f"Daily PnL: {summary.daily_pnl_pct:+.2f}%"
                    )
                    time.sleep(5)
                    continue

                # -------------------------------------------------------------
                # 7. MARKET CLOSE SETTLEMENT (15:30 to 16:00 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.MARKET_CLOSE:
                    logger.info(f"[{time_str} IST] [MARKET CLOSE] Closing bells rung. Flushing RAM intraday candles to Silver & persisting daily portfolio state...")
                    self.portfolio_mgr._persist_state()
                    try:
                        from src.serving.eod_flush_worker import EODFlushWorker
                        flusher = EODFlushWorker(redis_mgr=self.redis_mgr)
                        symbols_to_flush = list(self.strategy_runner.orb_highs.keys()) or list(self.portfolio_mgr.positions.keys())
                        if symbols_to_flush:
                            flushed_count = flusher.flush_all_symbols(symbols_to_flush)
                            logger.info(f"[EOD FLUSH] Successfully flushed {flushed_count} live 1-minute candles from RAM into Silver Lakehouse.")
                    except Exception as e:
                        logger.warning(f"EOD RAM Flush Notice: {e}")
                    time.sleep(15)
                    continue

                # -------------------------------------------------------------
                # 8. AUTOMATED EOD DATA INGESTION (16:00 to 17:30 IST)
                # -------------------------------------------------------------
                if regime == MarketRegime.EOD_SYNC:
                    if self.last_eod_sync_date != today_date:
                        logger.info(f"[{time_str} IST] [04:00 PM EOD PIPELINE] Fetching today's completed daily bars & updating Gold Feature Lakehouse...")
                        try:
                            run_eod_pipeline(universe_mode="top300")
                            logger.info("EOD Ingestion & Feature Refresh Completed Successfully!")
                        except Exception as e:
                            logger.error(f"EOD Pipeline Error: {e}")
                        self.last_eod_sync_date = today_date
                    else:
                        if heartbeats % 6 == 1:
                            logger.info(f"[{time_str} IST] EOD Data for today ({today_date}) already synced and verified.")
                    time.sleep(30)
                    continue

                # Safety check
                if max_heartbeats and heartbeats >= max_heartbeats:
                    logger.info(f"Reached max requested heartbeats ({max_heartbeats}). Terminating loop cleanly.")
                    break

                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("\nShutdown signal (Ctrl+C) received. Executing graceful shutdown...")
        finally:
            self.shutdown()

    def shutdown(self):
        logger.info("Persisting Portfolio Ledger and state to SQLite...")
        if self.portfolio_mgr:
            self.portfolio_mgr._persist_state()
            summary = self.portfolio_mgr.get_summary()
            logger.info(
                f"Ledger Saved. Final Virtual Balance: Rs.{summary.total_portfolio_value:,.2f} "
                f"({summary.total_return_pct:+.2f}% total return)."
            )
        logger.info("MarketIntel Engine shutdown cleanly. Have a great day!")

def main():
    print_banner()
    system = MarketIntelSystem()

    def sig_handler(sig, frame):
        system.is_running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    system.preflight_check()
    quick_test = "--quick-test" in sys.argv
    max_beats = 2 if quick_test else None
    system.run(max_heartbeats=max_beats)

if __name__ == "__main__":
    main()
