"""
MarketIntel AI: Database Initialization Utility
===============================================

This script syncs the SQLAlchemy ORM models with the live PostgreSQL 
database schema. It is typically run once during initial environment 
setup to generate all necessary tables (Stocks, Prices, Watchlists, Alerts).
"""

import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import Base, get_engine

def create_tables():
    """
    Connects to the PostgreSQL instance and creates all missing tables.
    Safe to run multiple times (it will not drop or overwrite existing tables).
    """
    engine = get_engine()
    print("Connecting to database and creating tables...")
    Base.metadata.create_all(engine)
    print("✅ All tables created successfully (Watchlists, Alerts, etc.).")

if __name__ == "__main__":
    create_tables()
