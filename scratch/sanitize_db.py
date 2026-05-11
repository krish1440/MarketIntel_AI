
import sys
import os
from sqlalchemy import text

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, get_engine

def sanitize_database():
    session = get_session()
    
    print("--- Starting Database Sanitization (Fundamentals) ---")
    
    try:
        # 1. Deduplicate historical_fundamentals
        print("Removing duplicates from historical_fundamentals...")
        dedup_sql = """
        DELETE FROM historical_fundamentals a
        USING (
            SELECT MIN(id) as min_id, stock_id, date
            FROM historical_fundamentals
            GROUP BY stock_id, date
            HAVING COUNT(*) > 1
        ) b
        WHERE a.stock_id = b.stock_id 
          AND a.date = b.date 
          AND a.id <> b.min_id;
        """
        session.execute(text(dedup_sql))
        session.commit()
        print("SUCCESS: Removed duplicates.")
        
        # 2. Add the Unique Constraint
        print("Applying Unique Constraint to database schema...")
        constraint_sql = "ALTER TABLE historical_fundamentals ADD CONSTRAINT _stock_date_uc UNIQUE (stock_id, date);"
        session.execute(text(constraint_sql))
        session.commit()
        print("SUCCESS: Unique Constraint applied successfully.")
            
    except Exception as e:
        print(f"ERROR: Sanitization failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    sanitize_database()
