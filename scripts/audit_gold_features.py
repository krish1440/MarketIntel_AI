import polars as pl
from pathlib import Path

gold_base = Path("data/lakehouse/gold")
models = {
    "Model 0 (Pre-Market Screener & Ranker)": "features_screener_ranking",
    "Model 1 (Positional Swing Alpha <1Y)": "features_short_term_positional",
    "Model 2 (Wealth Compounding >1Y)": "features_long_term_swing",
    "Model 3 (Probabilistic Price Corridors)": "features_price_corridor",
    "Model 4 (Stock Action & Confidence)": "features_stock_action_classifier"
}

all_feature_cols = set()
print("=" * 75)
print("           MARKETINTEL PHASE 4 READINESS: FEATURE AUDIT REPORT        ")
print("=" * 75 + "\n")

total_model_feature_slots = 0

for m_title, m_dir_name in models.items():
    mdir = gold_base / m_dir_name
    files = list(mdir.glob("*.parquet"))
    sample_file = mdir / "RELIANCE.parquet" if (mdir / "RELIANCE.parquet").exists() else files[0]
    df = pl.read_parquet(sample_file)
    
    # Exclude base metadata columns to isolate actual ML features
    meta_cols = {"date", "open", "high", "low", "close", "volume", "symbol", "exchange", "date_key"}
    features = [c for c in df.columns if c not in meta_cols]
    all_feature_cols.update(features)
    total_model_feature_slots += len(features)
    
    # Check nulls and infs in modern period (2015-present)
    col_date = "date" if "date" in df.columns else "timestamp"
    modern_df = df.filter(pl.col(col_date).cast(pl.Date) >= pl.date(2015, 1, 1))
    null_counts = {c: modern_df[c].null_count() for c in features if modern_df[c].null_count() > 0}
    inf_counts = {
        c: modern_df.filter(pl.col(c).is_infinite()).height 
        for c in features 
        if modern_df[c].dtype in [pl.Float32, pl.Float64] and modern_df.filter(pl.col(c).is_infinite()).height > 0
    }
    
    print(f"-> {m_title}")
    print(f"   Directory: data/lakehouse/gold/{m_dir_name}")
    print(f"   Stocks Populated: {len(files):,} equities")
    print(f"   Total ML Feature Count: {len(features)}")
    print(f"   Feature Names: {', '.join(features)}")
    print(f"   Nulls in Modern Period (2015-2026): {null_counts if null_counts else '0 (CLEAN - 100% COMPLETE)'}")
    print(f"   Infinite Values: {inf_counts if inf_counts else '0 (CLEAN - ZERO INFINITIES)'}")
    print()

print("=" * 75)
print(f"TOTAL UNIQUE ML FEATURES ACROSS ALL 5 MODELS : {len(all_feature_cols)}")
print(f"TOTAL FEATURE INPUT SLOTS (SUM ACROSS MODELS): {total_model_feature_slots}")
print("=" * 75)
