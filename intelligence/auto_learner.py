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
from models.train_price import train_model

class AutoLearner:
    """
    Background daemon that manages continuous learning for the intelligence models.

    It compares current database records against the last known state stored in 
    checkpoints, triggering retraining cycles when sufficient new data arrives.
    """
    def __init__(self, check_interval_seconds=3600):
        """
        Initializes the AutoLearner with a specified polling interval.

        Args:
            check_interval_seconds (int): How often (in seconds) to check the DB.
        """
        self.interval = check_interval_seconds
        self.metadata_path = 'models/checkpoints/metadata.json'
        
    def get_last_data_count(self):
        """
        Reads the previously processed row count from the model checkpoint metadata.

        Returns:
            int: The total number of historical price records at last training.
        """
        try:
            with open(self.metadata_path, 'r') as f:
                return json.load(f).get('last_data_count', 0)
        except:
            return 0

    def set_last_data_count(self, count):
        """
        Updates the model checkpoint metadata with the new row count.

        Args:
            count (int): The updated row count to persist.
        """
        try:
            with open(self.metadata_path, 'r') as f:
                meta = json.load(f)
            meta['last_data_count'] = count
            with open(self.metadata_path, 'w') as f:
                json.dump(meta, f)
        except:
            pass

    def run(self):
        """
        Starts the continuous polling loop. 
        
        It checks for new records every `self.interval` seconds and triggers
        the incremental training pipeline if threshold conditions are met.
        """
        print("Autonomous Learner Daemon Started...")
        while True:
            session = get_session()
            current_count = session.query(HistoricalPrice).count()
            last_count = self.get_last_data_count()
            
            # If we have at least 10 new data points across all stocks, retrain
            if current_count > last_count + 10:
                print(f"New data detected ({current_count} vs {last_count}). Starting background fine-tuning...")
                meta = train_model(incremental=True)
                if meta:
                    self.set_last_data_count(current_count)
                    print(f"Background training successful. New RMSE: {meta['rmse_currency']:.2f}")
            else:
                print(f"No significant new data. Heartbeat at {datetime.datetime.now().strftime('%H:%M:%S')}")
            
            session.close()
            time.sleep(self.interval)

if __name__ == "__main__":
    # Check every hour by default
    learner = AutoLearner(check_interval_seconds=3600)
    learner.run()
