import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import polars as pl
import lightgbm as lgb
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error, r2_score

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import settings
from src.models.data_splitter import DataSplitter

logger = logging.getLogger("TrainModel2")

class Model2CompoundingTrainer:
    """
    Trainer for Model 2: Long-Term Wealth Compounding Engine (> 1 Year holding).
    
    Identifies high-quality compounding franchises capable of multi-year outperformance
    with minimal structural drawdown risk.
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
        """Trains Model 2 on pre-2024 data and evaluates on 1-year forward holdout windows."""
        logger.info(f"Loading Model 2 dataset (max_symbols={max_symbols}, min_turnover={min_turnover_cr} Cr)...")
        train_df, test_df = self.splitter.load_dataset(
            model_id=2,
            max_symbols=max_symbols,
            min_turnover_cr=min_turnover_cr
        )

        features = self.splitter.get_feature_columns(train_df)
        logger.info(f"Model 2 training with {len(features)} ML features: {features}")

        train_clean = train_df.drop_nulls(subset=features + ["target_fwd_ret_252d"])
        test_clean = test_df.drop_nulls(subset=features + ["target_fwd_ret_252d"])

        X_train = train_clean.select(features).to_numpy()
        y_train = train_clean.select("target_fwd_ret_252d").to_series().to_numpy()

        X_test = test_clean.select(features).to_numpy()
        y_test = test_clean.select("target_fwd_ret_252d").to_series().to_numpy()

        logger.info(f"Train samples: {len(X_train):,} | Test Vault samples: {len(X_test):,}")

        reg = lgb.LGBMRegressor(
            objective="regression",
            n_estimators=300,
            learning_rate=0.03,
            num_leaves=31,
            max_depth=5,
            min_child_samples=50,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )

        logger.info("Training Model 2 Compounding Regressor...")
        reg.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            eval_names=["train", "test_vault"],
            callbacks=[
                lgb.early_stopping(stopping_rounds=30, verbose=True),
                lgb.log_evaluation(period=50)
            ]
        )

        preds_test = reg.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
        r2 = float(r2_score(y_test, preds_test))
        spearman_corr, _ = spearmanr(preds_test, y_test)

        # Top Quartile Compounding Alpha
        top_quartile_mask = preds_test >= np.quantile(preds_test, 0.75)
        top_quartile_ret = float(np.mean(y_test[top_quartile_mask])) * 100
        overall_mean_ret = float(np.mean(y_test)) * 100
        compounding_alpha = top_quartile_ret - overall_mean_ret

        # Feature Importance
        importance = dict(zip(features, [float(x) for x in reg.feature_importances_]))
        sorted_importance = dict(sorted(importance.items(), key=lambda item: item[1], reverse=True))

        metrics = {
            "model": "Model 2 (Wealth Compounding Engine > 1Y)",
            "test_vault_rmse": round(rmse, 4),
            "test_vault_r2": round(r2, 4),
            "spearman_rank_correlation": round(float(spearman_corr), 4),
            "top_quartile_1y_return_pct": round(top_quartile_ret, 2),
            "compounding_alpha_spread_pct": round(compounding_alpha, 2),
            "top_features": list(sorted_importance.keys())
        }

        # Save artifacts
        model_path = self.output_dir / "model2_compounding.txt"
        reg.booster_.save_model(str(model_path))

        report_path = self.output_dir / "model2_evaluation.json"
        with open(report_path, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info("=" * 70)
        logger.info("MODEL 2 STAGE 1 TRAINING & TEST VAULT AUDIT COMPLETE:")
        logger.info(f"  Spearman Rank Correlation: {spearman_corr:.4f}")
        logger.info(f"  Top Quartile 1Y Return   : {top_quartile_ret:.2f}%")
        logger.info(f"  Compounding Alpha Spread : {compounding_alpha:+.2f}%")
        logger.info(f"  Saved Model Artifact     : {model_path}")
        logger.info("=" * 70)

        return metrics

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    trainer = Model2CompoundingTrainer()
    trainer.train_and_evaluate(max_symbols=250)
