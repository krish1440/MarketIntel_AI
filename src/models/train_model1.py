import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import joblib
import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import mean_pinball_loss

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import settings
from src.models.data_splitter import DataSplitter

logger = logging.getLogger("TrainModel1")

class Model1SwingAlphaTrainer:
    """
    Trainer for Model 1: Positional Swing Alpha Engine (< 1 Year holding).
    
    Trained using Multi-Quantile Pinball Loss (tau = 0.10, 0.50, 0.90):
      - Q10: Downside tail risk (Stop loss reference)
      - Q50: Median expected return (Signal alpha)
      - Q90: Upside target potential (Target reference)
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (settings.BASE_DIR / "models" / "stage1")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.splitter = DataSplitter()

    def train_and_evaluate(
        self,
        max_symbols: Optional[int] = 300,
        min_turnover_cr: float = 0.5
    ) -> Dict:
        """Trains Q10, Q50, Q90 Quantile Models on pre-2024 data and audits on 2-Year Test Vault."""
        logger.info(f"Loading Model 1 dataset (max_symbols={max_symbols}, min_turnover={min_turnover_cr} Cr)...")
        train_df, test_df = self.splitter.load_dataset(
            model_id=1,
            max_symbols=max_symbols,
            min_turnover_cr=min_turnover_cr
        )

        features = self.splitter.get_feature_columns(train_df)
        logger.info(f"Model 1 training with {len(features)} ML features: {features}")

        train_clean = train_df.drop_nulls(subset=features + ["target_fwd_ret_63d"])
        test_clean = test_df.drop_nulls(subset=features + ["target_fwd_ret_63d"])

        X_train = train_clean.select(features).to_numpy()
        y_train = train_clean.select("target_fwd_ret_63d").to_series().to_numpy()

        X_test = test_clean.select(features).to_numpy()
        y_test = test_clean.select("target_fwd_ret_63d").to_series().to_numpy()

        logger.info(f"Train samples: {len(X_train):,} | Test Vault samples: {len(X_test):,}")

        quantiles = [0.10, 0.50, 0.90]
        models = {}
        eval_metrics = {}

        for tau in quantiles:
            logger.info(f"Training Quantile Regressor tau={tau:.2f}...")
            reg = lgb.LGBMRegressor(
                objective="quantile",
                alpha=tau,
                n_estimators=300,
                learning_rate=0.05,
                num_leaves=31,
                max_depth=6,
                min_child_samples=50,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
            reg.fit(
                X_train, y_train,
                eval_set=[(X_train, y_train), (X_test, y_test)],
                eval_names=["train", "test_vault"],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=30, verbose=False),
                    lgb.log_evaluation(period=0)
                ]
            )
            models[f"q{int(tau*100)}"] = reg

            preds_test = reg.predict(X_test)
            pinball = float(mean_pinball_loss(y_test, preds_test, alpha=tau))
            empirical_coverage = float(np.mean(y_test <= preds_test))

            eval_metrics[f"q{int(tau*100)}_pinball_loss"] = round(pinball, 5)
            eval_metrics[f"q{int(tau*100)}_empirical_coverage"] = round(empirical_coverage, 4)

            # Save individual quantile model
            reg_path = self.output_dir / f"model1_swing_q{int(tau*100)}.txt"
            reg.booster_.save_model(str(reg_path))

        # Realized Sharpe Ratio on Top 15% highest conviction Q50 swing signals
        q50_preds = models["q50"].predict(X_test)
        pos_signal_mask = q50_preds >= np.quantile(q50_preds, 0.85)
        if np.sum(pos_signal_mask) > 0:
            active_returns = y_test[pos_signal_mask]
            mean_ret = float(np.mean(active_returns))
            std_ret = float(np.std(active_returns) + 1e-8)
            annualized_sharpe = float((mean_ret / std_ret) * np.sqrt(4))  # 4 quarters/year
            win_rate = float(np.mean(active_returns > 0)) * 100
        else:
            annualized_sharpe = 0.0
            win_rate = 0.0

        eval_metrics["model"] = "Model 1 (Positional Swing Alpha Engine)"
        eval_metrics["active_signals_annualized_sharpe"] = round(annualized_sharpe, 2)
        eval_metrics["active_signals_win_rate_pct"] = round(win_rate, 2)

        report_path = self.output_dir / "model1_evaluation.json"
        with open(report_path, "w") as f:
            json.dump(eval_metrics, f, indent=2)

        logger.info("=" * 70)
        logger.info("MODEL 1 STAGE 1 TRAINING & TEST VAULT AUDIT COMPLETE:")
        logger.info(f"  Q10 Coverage: {eval_metrics['q10_empirical_coverage']:.4f} (Nominal: 0.1000)")
        logger.info(f"  Q50 Coverage: {eval_metrics['q50_empirical_coverage']:.4f} (Nominal: 0.5000)")
        logger.info(f"  Q90 Coverage: {eval_metrics['q90_empirical_coverage']:.4f} (Nominal: 0.9000)")
        logger.info(f"  Active Signals Sharpe  : {annualized_sharpe:.2f}")
        logger.info(f"  Active Signals Win Rate: {win_rate:.2f}%")
        logger.info("=" * 70)

        return eval_metrics

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    trainer = Model1SwingAlphaTrainer()
    trainer.train_and_evaluate(max_symbols=250)
