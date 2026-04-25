import sys
import os
import xgboost as xgb
import numpy as np

# Add parent directory to path for db and model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.train_fusion import generate_fusion_dataset
from db.schema import get_session, Stock

def update_models_incrementally():
    session = get_session()
    stocks = session.query(Stock).all()
    
    X_new, y_new = [], []
    for stock in stocks:
        print(f"Collecting new data for {stock.ticker}...")
        data = generate_fusion_dataset(session, stock.id)
        if data:
            X, y = data
            # Just take the last 5 days for incremental update
            X_new.extend(X[-5:])
            y_new.extend(y[-5:])
            
    if not X_new:
        print("No new data for incremental learning.")
        return

    X_new = np.array(X_new)
    y_new = np.array(y_new)
    
    # Load existing model and update
    model = xgb.XGBClassifier()
    checkpoint_path = 'models/checkpoints/fusion_model.json'
    
    if os.path.exists(checkpoint_path):
        model.load_model(checkpoint_path)
        # Incremental fit (using the existing model as a base)
        model.fit(X_new, y_new, xgb_model=model.get_booster())
        print("Model updated incrementally.")
    else:
        model.fit(X_new, y_new)
        print("New model trained.")
        
    model.save_model(checkpoint_path)
    session.close()

if __name__ == "__main__":
    update_models_incrementally()
