"""
MARKETINTEL AI: TABLE CREATION UTILITY
======================================
Syncs the SQLAlchemy models with the live database schema.
"""

import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import Base, get_engine

def create_tables():
    engine = get_engine()
    print("Connecting to database and creating tables...")
    Base.metadata.create_all(engine)
    print("✅ All tables created successfully (Watchlists, Alerts, etc.).")

if __name__ == "__main__":
    create_tables()
