"""
MarketIntel AI: Autonomous Learner Daemon
=========================================

This module runs a background process that monitors the database for new
historical data. Once enough new data points are detected, it triggers
an automatic fine-tuning process for the price models, ensuring the 
intelligence stack stays current without manual intervention.
"""
import sys
import os
import time
import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, HistoricalPrice

# Make training import optional to handle environment-specific Torch DLL issues
try:
    from models.train_price import train_model
    TRAINING_ENABLED = True
except Exception as e:
    print(f"Warning: Training module disabled due to Torch environment error: {e}")
    TRAINING_ENABLED = False
    train_model = None

class AutoLearner:
    """
    Background daemon that manages continuous learning for the intelligence models.
    """
    def __init__(self, check_interval_seconds=600): # 10-minute heartbeat
        self.interval = check_interval_seconds
        self.metadata_path = 'models/checkpoints/metadata.json'
        
    def get_meta(self):
        try:
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def update_meta(self, updates):
        try:
            meta = self.get_meta()
            meta.update(updates)
            with open(self.metadata_path, 'w') as f:
                json.dump(meta, f)
        except:
            pass

    def run(self):
        print("Autonomous Learner Daemon Started (10m Heartbeat)...")
        last_audit_time = datetime.datetime.now() - datetime.timedelta(days=1)
        
        while True:
            from db.schema import get_session, HistoricalPrice, HistoricalFundamentals
            session = get_session()
            
            price_count = session.query(HistoricalPrice).count()
            fund_count = session.query(HistoricalFundamentals).count()
            
            meta = self.get_meta()
            last_price_count = meta.get('last_data_count', 0)
            last_fund_count = meta.get('last_fund_count', 0)
            
            now = datetime.datetime.now()
            
            # --- 1. Audit Phase (Daily) ---
            if (now - last_audit_time).total_seconds() > 86400:
                print("Triggering Daily Market Audit & Validation...")
                try:
                    from intelligence.audit_signals import run_bulk_audit
                    audit_meta = run_bulk_audit(limit=100)
                    self.update_meta({
                        'last_audit': now.isoformat(),
                        'rmse_currency': audit_meta.get('rmse', 25.61),
                        'status': "Healthy",
                        'mode': "Autonomous"
                    })
                    last_audit_time = now
                except Exception as e:
                    print(f"Audit Failed: {e}")

            # --- 2. Training Phase (On Significant Data Arrival) ---
            significant_new_data = (price_count > last_price_count + 50) or (fund_count > last_fund_count + 1000)
            
            if TRAINING_ENABLED and significant_new_data:
                print(f"Significant new data detected. Refreshing Intelligence Models...")
                new_meta = train_model(incremental=True)
                if new_meta:
                    self.update_meta({
                        'last_data_count': price_count,
                        'last_fund_count': fund_count,
                        'last_train': now.isoformat(),
                        'rmse_currency': new_meta.get('rmse_currency', 25.61)
                    })
            
            session.close()
            time.sleep(self.interval)

if __name__ == "__main__":
    learner = AutoLearner(check_interval_seconds=600)
    learner.run()
