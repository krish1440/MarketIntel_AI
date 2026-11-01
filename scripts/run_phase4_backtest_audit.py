import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.models.train_model0 import Model0RankerTrainer
from src.models.train_model4 import Model4ClassifierTrainer
from src.models.train_model1 import Model1SwingAlphaTrainer
from src.models.train_model2 import Model2CompoundingTrainer
from src.models.train_model3 import Model3CorridorTrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Phase4BacktestAudit")

def run_phase4_audit(max_symbols: int = 300) -> Dict:
    """
    Executes the comprehensive Stage 1 Training and 2-Year Out-Of-Sample Holdout Audit.
    Evaluates all 5 decoupled AI models against the Jan 1, 2024 - Present test vault.
    """
    audit_start = time.time()
    results = {}

    print("=" * 80)
    print("      MARKETINTEL PHASE 4: STAGE 1 TRAINING & 2-YEAR HOLDOUT AUDIT     ")
    print("=" * 80)
    print(f"Training Partition   : Listing Day (up to 30 Years) -> Dec 31, 2023")
    print(f"Embargo Purge Window : 63 Trading Days (~3 Months) Ahead of Jan 1, 2024")
    print(f"2-Year Test Vault    : Jan 1, 2024 -> Nov 2026 (100% Unseen Data)")
    print(f"Liquid Equity Universe: Top {max_symbols} Mapped NSE Stocks")
    print("=" * 80 + "\n")

    # 1. Model 0: Screener & LambdaMART Ranker
    logger.info(">>> [1/5] TRAINING & AUDITING MODEL 0 (SCREENER RANKER)...")
    m0_trainer = Model0RankerTrainer()
    results["model0"] = m0_trainer.train_and_evaluate(max_symbols=max_symbols)

    # 2. Model 4: Stock Action & Confidence Classifier
    logger.info(">>> [2/5] TRAINING & AUDITING MODEL 4 (ACTION & CONFIDENCE CLASSIFIER)...")
    m4_trainer = Model4ClassifierTrainer()
    results["model4"] = m4_trainer.train_and_evaluate(max_symbols=max_symbols)

    # 3. Model 1: Positional Swing Alpha Engine
    logger.info(">>> [3/5] TRAINING & AUDITING MODEL 1 (POSITIONAL SWING ALPHA)...")
    m1_trainer = Model1SwingAlphaTrainer()
    results["model1"] = m1_trainer.train_and_evaluate(max_symbols=max_symbols)

    # 4. Model 2: Wealth Compounding Engine
    logger.info(">>> [4/5] TRAINING & AUDITING MODEL 2 (WEALTH COMPOUNDING > 1Y)...")
    m2_trainer = Model2CompoundingTrainer()
    results["model2"] = m2_trainer.train_and_evaluate(max_symbols=max_symbols)

    # 5. Model 3: Probabilistic Price Corridors
    logger.info(">>> [5/5] TRAINING & AUDITING MODEL 3 (PRICE CORRIDOR ENVELOPES)...")
    m3_trainer = Model3CorridorTrainer()
    results["model3"] = m3_trainer.train_and_evaluate(max_symbols=max_symbols)

    total_time = time.time() - audit_start
    results["audit_duration_seconds"] = round(total_time, 2)

    # Save consolidated audit master report
    audit_file = settings.BASE_DIR / "models" / "stage1" / "phase4_audit_master.json"
    with open(audit_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("               PHASE 4 AUDIT SUMMARY: 2-YEAR OUT-OF-SAMPLE VAULT       ")
    print("=" * 80)
    print(f"1. Model 0 (LambdaMART Screener)  : NDCG@20 = {results['model0']['test_vault_ndcg@20']:.4f} | 5-Day Decile Alpha = {results['model0']['mean_5d_alpha_spread_pct']:+.2f}%")
    print(f"2. Model 4 (Action & Confidence)  : Balanced Acc = {results['model4']['test_vault_balanced_accuracy']*100:.2f}% | High-Conf Acc = {results['model4']['high_confidence_accuracy']*100:.2f}%")
    print(f"3. Model 1 (Positional Alpha)     : Realized Sharpe = {results['model1']['active_signals_annualized_sharpe']:.2f} | Win Rate = {results['model1']['active_signals_win_rate_pct']:.2f}%")
    print(f"4. Model 2 (Wealth Compounding)   : Spearman Corr = {results['model2']['spearman_rank_correlation']:.4f} | Top Quartile 1Y Return = {results['model2']['top_quartile_1y_return_pct']:.2f}%")
    print(f"5. Model 3 (Price Corridors)      : P05-P95 Band Coverage = {results['model3']['nominal_90_band_coverage_pct']:.2f}% (Nominal: 90%)")
    print(f"Total Audit Execution Time       : {total_time:.2f} seconds")
    print(f"Consolidated Report Saved To     : {audit_file}")
    print("=" * 80)

    return results

if __name__ == "__main__":
    run_phase4_audit(max_symbols=300)

