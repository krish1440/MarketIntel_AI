import os
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.config.settings import settings
from src.serving.redis_manager import RedisManager
from src.execution.portfolio_manager import VirtualPortfolioManager
from src.execution.strategy_runner import AIStrategyRunner

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
   INSTITUTIONAL QUANTITATIVE MARKET INTELLIGENCE & AI PAPER TRADING
   Execution Mode: STRICT PAPER TRADING (Zero Real Money at Risk)
   Capital: Rs.10,00,000 INR Virtual Budget | Local-First Architecture
================================================================================
"""
    print(banner)

class MarketIntelSystem:
    def __init__(self):
        self.is_running = True
        self.redis_mgr = None
        self.portfolio_mgr = None
        self.strategy_runner = None

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

        # 3. Model Registry Verification
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

        logger.info(">>> ALL PRE-FLIGHT CHECKS PASSED. SYSTEM READY FOR LIVE EXECUTION <<<\n")

    def run(self, max_heartbeats: Optional[int] = None):
        logger.info("MarketIntel Paper Trading Loop is now ACTIVE.")
        logger.info("Awaiting Market Sessions (09:08 AM Pre-Market, 09:15-09:30 ORB, 09:30-15:30 Continuous Execution).")
        logger.info("Press Ctrl+C to safely pause and persist ledger.\n")

        heartbeats = 0
        try:
            while self.is_running:
                heartbeats += 1
                now = datetime.now()
                # Log periodic status
                summary = self.portfolio_mgr.get_summary()
                logger.info(
                    f"[HEARTBEAT #{heartbeats}] {now.strftime('%H:%M:%S')} IST | "
                    f"Portfolio Value: Rs.{summary.total_portfolio_value:,.2f} | "
                    f"Cash: Rs.{summary.current_cash:,.2f} | Open Trades: {summary.open_positions_count} | "
                    f"Daily PnL: {summary.daily_pnl_pct:+.2f}%"
                )

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
    # Check if run with --test-quick flag
    quick_test = "--quick-test" in sys.argv
    max_beats = 2 if quick_test else None
    system.run(max_heartbeats=max_beats)

if __name__ == "__main__":
    main()
