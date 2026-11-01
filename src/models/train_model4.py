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
from sklearn.metrics import (
    classification_report,
    log_loss,
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix
)
from sklearn.calibration import CalibratedClassifierCV

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import settings
from src.models.data_splitter import DataSplitter

logger = logging.getLogger("TrainModel4")

CLASS_NAMES = ["STRONG_SELL", "SELL", "HOLD", "BUY", "STRONG_BUY"]

class Model4ClassifierTrainer:
    """
    Trainer for Model 4: Universal Stock Action & Confidence Classifier.
    
    Generates high-precision trade actions:
      - Class 0: STRONG_SELL
      - Class 1: SELL
      - Class 2: HOLD (Neutral consolidation)
      - Class 3: BUY
      - Class 4: STRONG_BUY (High momentum, tight stop potential)
      
    Calibrated with Platt scaling to produce reliable probability confidence scores.
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
        """Trains Model 4 on historical data (<2024) and evaluates on the 2024-2026 Test Vault."""
        logger.info(f"Loading Model 4 dataset (max_symbols={max_symbols}, min_turnover={min_turnover_cr} Cr)...")
        train_df, test_df = self.splitter.load_dataset(
            model_id=4,
            max_symbols=max_symbols,
            min_turnover_cr=min_turnover_cr
        )

        features = self.splitter.get_feature_columns(train_df)
        logger.info(f"Model 4 training with {len(features)} ML features: {features}")

        # Drop any remaining nulls in train or test
        train_clean = train_df.drop_nulls(subset=features + ["target_action_class"])
        test_clean = test_df.drop_nulls(subset=features + ["target_action_class"])

        X_train = train_clean.select(features).to_numpy()
        y_train = train_clean.select("target_action_class").to_series().to_numpy().astype(int)

        X_test = test_clean.select(features).to_numpy()
        y_test = test_clean.select("target_action_class").to_series().to_numpy().astype(int)

        logger.info(f"Train samples: {len(X_train):,} | Test Vault samples: {len(X_test):,}")

        # Class balance inspection
        unique, counts = np.unique(y_train, return_counts=True)
        dist = {CLASS_NAMES[k]: int(v) for k, v in zip(unique, counts)}
        logger.info(f"Train Class Distribution: {dist}")

        # LightGBM Classifier
        clf = lgb.LGBMClassifier(
            objective="multiclass",
            num_class=5,
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

        logger.info(f"Training and Calibrating Model 4 via Platt Scaling (cv=3)...")
        # Subsample to 200,000 if training data is massive for ultra-fast training
        if len(X_train) > 200000:
            np.random.seed(42)
            idx = np.random.choice(len(X_train), size=200000, replace=False)
            X_train_fit = X_train[idx]
            y_train_fit = y_train[idx]
        else:
            X_train_fit = X_train
            y_train_fit = y_train

        calibrated_clf = CalibratedClassifierCV(clf, cv=3, method="sigmoid")
        calibrated_clf.fit(X_train_fit, y_train_fit)

        # Predictions on unseen test vault
        y_pred = calibrated_clf.predict(X_test)
        y_proba = calibrated_clf.predict_proba(X_test)
        confidence = np.max(y_proba, axis=1)

        # Metrics
        acc = float(accuracy_score(y_test, y_pred))
        bal_acc = float(balanced_accuracy_score(y_test, y_pred))
        loss = float(log_loss(y_test, y_proba))

        # High confidence precision (>65% confidence)
        high_conf_mask = confidence >= 0.65
        if np.sum(high_conf_mask) > 0:
            high_conf_acc = float(accuracy_score(y_test[high_conf_mask], y_pred[high_conf_mask]))
            high_conf_share = float(np.mean(high_conf_mask)) * 100
        else:
            high_conf_acc = acc
            high_conf_share = 0.0

        # Feature Importance (averaged across calibrated folds)
        mean_importances = np.mean([c.estimator.feature_importances_ for c in calibrated_clf.calibrated_classifiers_], axis=0)
        importance = dict(zip(features, [float(x) for x in mean_importances]))
        sorted_importance = dict(sorted(importance.items(), key=lambda item: item[1], reverse=True))

        metrics = {
            "model": "Model 4 (Stock Action & Confidence Classifier)",
            "test_vault_accuracy": round(acc, 4),
            "test_vault_balanced_accuracy": round(bal_acc, 4),
            "test_vault_log_loss": round(loss, 4),
            "high_confidence_accuracy": round(high_conf_acc, 4),
            "high_confidence_signal_share_pct": round(high_conf_share, 2),
            "top_10_features_by_importance": list(sorted_importance.keys())[:10]
        }

        # Save artifacts
        model_path = self.output_dir / "model4_classifier.joblib"
        joblib.dump(calibrated_clf, model_path)

        report_path = self.output_dir / "model4_evaluation.json"
        with open(report_path, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info("=" * 70)
        logger.info("MODEL 4 STAGE 1 TRAINING & TEST VAULT AUDIT COMPLETE:")
        logger.info(f"  Overall Accuracy        : {acc*100:.2f}%")
        logger.info(f"  Balanced Accuracy       : {bal_acc*100:.2f}%")
        logger.info(f"  Log Loss                : {loss:.4f}")
        logger.info(f"  High Confidence Accuracy: {high_conf_acc*100:.2f}% (on {high_conf_share:.1f}% of bars)")
        logger.info(f"  Saved Calibrated Model  : {model_path}")
        logger.info("=" * 70)

        return metrics

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    trainer = Model4ClassifierTrainer()
    trainer.train_and_evaluate(max_symbols=250)
