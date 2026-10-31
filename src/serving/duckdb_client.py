import logging
import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)

class DuckDBClient:
    """
    High-Performance Analytical Query Engine for Medallion Lakehouse.
    Uses DuckDB's native zero-copy Parquet reader with partition pruning.
    Enables sub-second SQL queries across millions of historical bars.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.DATA_DIR / "market_intel.duckdb")
        self.conn = duckdb.connect(database=self.db_path, read_only=False)
        self._configure_engine()
        self._register_views()

    def _configure_engine(self):
        """Optimizes DuckDB for multi-core local execution and memory limits."""
        try:
            self.conn.execute("SET preserve_insertion_order=false;")
            self.conn.execute("SET threads TO 4;")
            self.conn.execute("SET memory_limit='6GB';")
        except Exception as e:
            logger.warning(f"Error configuring DuckDB settings: {e}")

    def _register_views(self):
        """Registers SQL Views mapping to Silver and Gold Lakehouse Parquet paths."""
        logger.info("Registering DuckDB Lakehouse SQL Views...")
        
        # 1. Silver 1D OHLCV
        silver_1d_glob = str(settings.SILVER_DIR / "ohlcv_1d" / "*.parquet").replace("\\", "/")
        try:
            self.conn.execute(f"""
                CREATE OR REPLACE VIEW silver_ohlcv_1d AS 
                SELECT * FROM read_parquet('{silver_1d_glob}', hive_partitioning=false, union_by_name=true);
            """)
        except Exception as e:
            logger.debug(f"Could not register silver_ohlcv_1d view: {e}")

        # 2. Silver Macro Indices
        macro_path = str(settings.SILVER_DIR / "macro" / "macro_indices.parquet").replace("\\", "/")
        try:
            self.conn.execute(f"""
                CREATE OR REPLACE VIEW silver_macro_indices AS 
                SELECT * FROM read_parquet('{macro_path}');
            """)
        except Exception as e:
            logger.debug(f"Could not register silver_macro_indices view: {e}")

        # 3. Silver Security Master
        master_path = str(settings.SILVER_DIR / "master" / "stock_sector_mapping.parquet").replace("\\", "/")
        try:
            self.conn.execute(f"""
                CREATE OR REPLACE VIEW silver_security_master AS 
                SELECT * FROM read_parquet('{master_path}');
            """)
        except Exception as e:
            logger.debug(f"Could not register silver_security_master view: {e}")

    def query(self, sql: str) -> duckdb.DuckDBPyRelation:
        """Executes arbitrary SQL query and returns DuckDB relation."""
        return self.conn.execute(sql)

    def query_df(self, sql: str):
        """Executes SQL and returns Polars DataFrame."""
        return self.conn.execute(sql).pl()

    def get_stock_history(self, symbol: str, start_date: str = "2020-01-01") -> duckdb.DuckDBPyRelation:
        """Fetch stock daily history."""
        file_path = str(settings.SILVER_DIR / "ohlcv_1d" / f"{symbol}.parquet").replace("\\", "/")
        sql = f"""
            SELECT * FROM read_parquet('{file_path}') 
            WHERE timestamp >= '{start_date}' 
            ORDER BY timestamp ASC;
        """
        return self.conn.execute(sql)

    def close(self):
        """Closes DuckDB connection cleanly."""
        if self.conn:
            self.conn.close()
