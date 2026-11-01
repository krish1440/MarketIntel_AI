import sys
import logging
from pathlib import Path

# Ensure project root in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.mlops.champion_governance import ChampionGovernanceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TestGovernance")

def test_governance():
    logger.info("Initializing ChampionGovernanceEngine...")
    engine = ChampionGovernanceEngine()
    
    logger.info("Running Screener Tournament...")
    result = engine.run_weekly_screener_tournament()
    
    logger.info(f"Tournament Finished! Target: {result.target_model}, Promoted: {result.promoted}")
    logger.info(f"Champion Sharpe: {result.champion_metrics.sharpe_ratio}, Challenger Sharpe: {result.challenger_metrics.sharpe_ratio}")
    logger.info(f"Reason: {result.promotion_reason}")

    assert engine.history_file.exists(), "Tournament history file was not created"
    logger.info("MLOps Champion vs Challenger Governance verified successfully!")
    print("ALL MLOPS GOVERNANCE TESTS PASSED!")

if __name__ == "__main__":
    test_governance()
