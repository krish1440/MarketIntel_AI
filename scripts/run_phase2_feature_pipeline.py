import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.features.polars_engine import PolarsFeatureEngine
from src.serving.duckdb_client import DuckDBClient

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("Phase2Pipeline")

    logger.info("=" * 70)
    logger.info("LAUNCHING PHASE 2: POLARS FEATURE ENGINE & GOLD LAKEHOUSE CREATION")
    logger.info("=" * 70)

    # 1. Run Master Feature Engine
    engine = PolarsFeatureEngine()
    engine.process_all_stocks()

    # 2. Test DuckDB Query Engine
    logger.info("Initializing DuckDB Analytical Client...")
    duck = DuckDBClient()
    res = duck.query("SELECT COUNT(*) FROM silver_security_master;").fetchone()
    logger.info(f"DuckDB Verified: Connected to {res[0]} securities in Silver Master.")
    duck.close()

    logger.info("=" * 70)
    logger.info("PHASE 2 COMPLETED SUCCESSFULLY!")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()

