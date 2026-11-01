import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import logging
from src.models.data_splitter import DataSplitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
splitter = DataSplitter()

for mid in [0, 1, 2, 3, 4]:
    print(f"\n{'='*20} Testing Model {mid} Splitter {'='*20}")
    train_df, test_df = splitter.load_dataset(model_id=mid, max_symbols=5)
    features = splitter.get_feature_columns(train_df)
    print(f"Train shape: {train_df.shape}, Test shape: {test_df.shape}")
    print(f"Feature count: {len(features)}")
    target_cols = [c for c in train_df.columns if c.startswith("target_")]
    print(f"Target columns: {target_cols}")
    train_max = train_df["date"].max()
    test_min = test_df["date"].min()
    print(f"Train max date: {train_max} | Test min date: {test_min}")
    assert train_max < test_min, "LEAKAGE DETECTED: Train overlap!"
    print("Zero-Leakage Assertion: PASSED")
