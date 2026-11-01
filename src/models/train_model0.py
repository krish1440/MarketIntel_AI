import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import ndcg_score

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import settings
from src.models.data_splitter import DataSplitter

logger = logging.getLogger("TrainModel0")

class Model0RankerTrainer:
    """
    Trainer for Model 0: Pre-Market Screener & LambdaMART Ranker.
    
    Ranks the entire equity universe every morning before open into:
      - Top Long Opportunities (Rank 1-20)
      - Avoid / Short Lists
    
    Training Objective: lambdarank (LambdaMART) with NDCG@20.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (settings.BASE_DIR / "models" / "stage1")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.splitter = DataSplitter()

    def prepare_ranking_data(
        self, 
        df: pl.DataFrame, 
        features: List[str]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
        """
        Sorts by date and symbol to create group-structured arrays for LightGBM LambdaMART.
        Converts continuous forward returns into 5 discrete relevance tiers (0 to 4).
        """
        # Ensure sorted by date
        df_sorted = df.sort(["date", "symbol"])

        # Filter dates that have at least 10 stocks so ranking queries are statistically meaningful
        date_counts = df_sorted.group_by("date").len()
        valid_dates = date_counts.filter(pl.col("len") >= 10).select("date")
        df_sorted = df_sorted.join(valid_dates, on="date", how="inner").sort(["date", "symbol"])

        # Compute per-day percentile ranking buckets for 5-day forward return (0 to 4)
        pct_rank = pl.col("target_fwd_ret_5d").rank("ordinal").over("date") / pl.len().over("date")
        df_sorted = df_sorted.with_columns(
            (pct_rank * 5.0).floor().cast(pl.Int32).clip(0, 4).alias("relevance_tier")
        ).filter(pl.col("relevance_tier").is_not_null())

        # Extract group sizes (counts per date)
        group_counts = (
            df_sorted.group_by("date", maintain_order=True)
            .len()
            .select("len")
            .to_series()
            .to_list()
        )

        X = df_sorted.select(features).to_numpy()
        y = df_sorted.select("relevance_tier").to_series().to_numpy()
        dates = df_sorted.select("date").to_series().to_numpy()

        return X, y, df_sorted, group_counts

    def train_and_evaluate(
        self, 
        max_symbols: Optional[int] = 300,
        min_turnover_cr: float = 0.5
    ) -> Dict:
        """Runs Stage 1 Training and Out-Of-Sample Test Vault Evaluation."""
        logger.info(f"Loading Model 0 dataset (max_symbols={max_symbols}, min_turnover={min_turnover_cr} Cr)...")
        train_df, test_df = self.splitter.load_dataset(
            model_id=0,
            max_symbols=max_symbols,
            min_turnover_cr=min_turnover_cr
        )

        features = self.splitter.get_feature_columns(train_df)
        logger.info(f"Model 0 training with {len(features)} ML features: {features}")

        logger.info("Formatting LambdaMART query groups for Train partition...")
        X_train, y_train, df_train_sorted, groups_train = self.prepare_ranking_data(train_df, features)

        logger.info("Formatting LambdaMART query groups for 2-Year Test Vault...")
        X_test, y_test, df_test_sorted, groups_test = self.prepare_ranking_data(test_df, features)

        logger.info(f"Train samples: {len(X_train):,} in {len(groups_train):,} daily groups.")
        logger.info(f"Test Vault samples: {len(X_test):,} in {len(groups_test):,} daily groups.")

        # LightGBM LambdaMART parameters
        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [5, 10, 20],
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 6,
            "min_data_in_leaf": 50,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 1,
            "verbosity": -1,
            "random_state": 42,
            "n_jobs": -1
        }

        train_data = lgb.Dataset(X_train, label=y_train, group=groups_train, feature_name=features)
        test_data = lgb.Dataset(X_test, label=y_test, group=groups_test, reference=train_data, feature_name=features)

        logger.info("Training Model 0 LightGBM LambdaMART Ranker...")
        evals_result = {}
        model = lgb.train(
            params,
            train_data,
            num_boost_round=400,
            valid_sets=[train_data, test_data],
            valid_names=["train", "test_vault"],
            callbacks=[
                lgb.early_stopping(stopping_rounds=40, verbose=True),
                lgb.log_evaluation(period=50),
                lgb.record_evaluation(evals_result)
            ]
        )

        # Feature Importance
        importance = dict(zip(features, [float(x) for x in model.feature_importance(importance_type="gain")]))
        sorted_importance = dict(sorted(importance.items(), key=lambda item: item[1], reverse=True))

        # Out-Of-Sample Evaluation Metrics
        test_ndcg_20 = float(evals_result["test_vault"]["ndcg@20"][-1])
        test_ndcg_10 = float(evals_result["test_vault"]["ndcg@10"][-1])
        test_ndcg_5 = float(evals_result["test_vault"]["ndcg@5"][-1])

        # Top Decile Return Spread Test
        preds_test = model.predict(X_test)
        test_df_eval = df_test_sorted.with_columns([
            pl.Series("predicted_rank_score", preds_test)
        ])

        # Top 10% vs Bottom 10% daily forward returns
        daily_spread = (
            test_df_eval.group_by("date")
            .agg([
                pl.col("target_fwd_ret_5d").filter(
                    pl.col("predicted_rank_score") >= pl.col("predicted_rank_score").quantile(0.90)
                ).mean().alias("top_decile_fwd_ret"),
                pl.col("target_fwd_ret_5d").filter(
                    pl.col("predicted_rank_score") <= pl.col("predicted_rank_score").quantile(0.10)
                ).mean().alias("bottom_decile_fwd_ret")
            ])
            .with_columns(
                (pl.col("top_decile_fwd_ret") - pl.col("bottom_decile_fwd_ret")).alias("alpha_spread")
            )
        )

        mean_alpha_spread = float(daily_spread["alpha_spread"].mean()) * 100  # in %
        annualized_alpha = mean_alpha_spread * 50  # ~50 weekly periods/year

        metrics = {
            "model": "Model 0 (Pre-Market Screener & LambdaMART Ranker)",
            "test_vault_ndcg@5": round(test_ndcg_5, 4),
            "test_vault_ndcg@10": round(test_ndcg_10, 4),
            "test_vault_ndcg@20": round(test_ndcg_20, 4),
            "mean_5d_alpha_spread_pct": round(mean_alpha_spread, 2),
            "annualized_top_decile_alpha_pct": round(annualized_alpha, 2),
            "top_10_features_by_gain": list(sorted_importance.keys())[:10]
        }

        # Save model and report
        model_path = self.output_dir / "model0_screener.txt"
        model.save_model(str(model_path))

        report_path = self.output_dir / "model0_evaluation.json"
        with open(report_path, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info("=" * 70)
        logger.info(f"MODEL 0 STAGE 1 TRAINING & TEST VAULT AUDIT COMPLETE:")
        logger.info(f"  NDCG@5 : {test_ndcg_5:.4f}")
        logger.info(f"  NDCG@10: {test_ndcg_10:.4f}")
        logger.info(f"  NDCG@20: {test_ndcg_20:.4f}")
        logger.info(f"  Mean 5-Day Top Decile Alpha Spread: {mean_alpha_spread:+.2f}%")
        logger.info(f"  Annualized Decile Alpha: {annualized_alpha:+.2f}%")
        logger.info(f"  Saved Model Artifact: {model_path}")
        logger.info("=" * 70)

        return metrics

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    trainer = Model0RankerTrainer()
    trainer.train_and_evaluate(max_symbols=250)
