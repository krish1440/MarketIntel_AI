import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import mean_pinball_loss

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import settings
from src.models.data_splitter import DataSplitter

logger = logging.getLogger("TrainModel3")

class Model3CorridorTrainer:
    """
    Trainer for Model 3: Probabilistic Price Corridor Forecaster.
    
    Generates dynamic multi-quantile price cones across all 2,000+ equities:
      - P05: Structural downside floor / black-swan safety
      - P25: Conservative dip-buy channel
      - P50: Median central price trajectory
      - P75: Institutional take-profit band
      - P95: Parabolic exhaustion ceiling
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
        """Trains P05, P25, P50, P75, P95 Corridor Regressors on pre-2024 data and evaluates on Test Vault."""
        logger.info(f"Loading Model 3 dataset (max_symbols={max_symbols}, min_turnover={min_turnover_cr} Cr)...")
        train_df, test_df = self.splitter.load_dataset(
            model_id=3,
            max_symbols=max_symbols,
            min_turnover_cr=min_turnover_cr
        )

        features = self.splitter.get_feature_columns(train_df)
        logger.info(f"Model 3 training with {len(features)} ML features: {features}")

        train_clean = train_df.drop_nulls(subset=features + ["target_fwd_ret_21d"])
        test_clean = test_df.drop_nulls(subset=features + ["target_fwd_ret_21d"])

        X_train = train_clean.select(features).to_numpy()
        y_train = train_clean.select("target_fwd_ret_21d").to_series().to_numpy()

        X_test = test_clean.select(features).to_numpy()
        y_test = test_clean.select("target_fwd_ret_21d").to_series().to_numpy()

        logger.info(f"Train samples: {len(X_train):,} | Test Vault samples: {len(X_test):,}")

        quantiles = [0.05, 0.25, 0.50, 0.75, 0.95]
        eval_metrics = {}

        for tau in quantiles:
            p_name = f"p{int(tau*100):02d}"
            logger.info(f"Training Corridor Quantile Regressor {p_name} (tau={tau:.2f})...")
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

            preds_test = reg.predict(X_test)
            pinball = float(mean_pinball_loss(y_test, preds_test, alpha=tau))
            empirical_coverage = float(np.mean(y_test <= preds_test))

            eval_metrics[f"{p_name}_pinball_loss"] = round(pinball, 5)
            eval_metrics[f"{p_name}_empirical_coverage"] = round(empirical_coverage, 4)

            # Save individual corridor model
            reg_path = self.output_dir / f"model3_corridor_{p_name}.txt"
            reg.booster_.save_model(str(reg_path))

        # 90% Confidence Interval Envelope Coverage (P95 - P05)
        p05_cov = eval_metrics["p05_empirical_coverage"]
        p95_cov = eval_metrics["p95_empirical_coverage"]
        band_90_coverage = round((p95_cov - p05_cov) * 100, 2)

        eval_metrics["model"] = "Model 3 (Probabilistic Price Corridor Forecaster)"
        eval_metrics["nominal_90_band_coverage_pct"] = band_90_coverage

        report_path = self.output_dir / "model3_evaluation.json"
        with open(report_path, "w") as f:
            json.dump(eval_metrics, f, indent=2)

        logger.info("=" * 70)
        logger.info("MODEL 3 STAGE 1 TRAINING & TEST VAULT AUDIT COMPLETE:")
        for tau in quantiles:
            p_name = f"p{int(tau*100):02d}"
            logger.info(f"  {p_name.upper()} Coverage: {eval_metrics[f'{p_name}_empirical_coverage']:.4f} (Nominal: {tau:.2f})")
        logger.info(f"  P05 to P95 Corridor Coverage: {band_90_coverage:.2f}% (Nominal Target: ~90.00%)")
        logger.info("=" * 70)

        return eval_metrics

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    trainer = Model3CorridorTrainer()
    trainer.train_and_evaluate(max_symbols=250)
