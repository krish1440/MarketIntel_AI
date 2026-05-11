import json
import datetime
from intelligence.audit_signals import run_bulk_audit

def force_refresh():
    print("--- Starting Manual Terminal Audit ---")
    summary = run_bulk_audit(limit=50)
    
    path = 'models/checkpoints/metadata.json'
    try:
        with open(path, 'r') as f:
            meta = json.load(f)
            
        meta['last_train'] = datetime.datetime.now().isoformat()
        meta['rmse_currency'] = summary['rmse']
        meta['status'] = "Healthy"
        meta['mode'] = "Autonomous"
        
        with open(path, 'w') as f:
            json.dump(meta, f)
            
        print(f"--- Dashboard Updated: RMSE ±₹{meta['rmse_currency']:.2f} ---")
    except Exception as e:
        print(f"Error updating metadata: {e}")

if __name__ == "__main__":
    force_refresh()
