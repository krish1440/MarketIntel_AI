"""
MarketIntel AI: System Health Check
===================================
A diagnostic utility to verify the integrity of the local environment.
Checks: Database Connection, API Reachability, and AI Model Readiness.
"""

import requests
import sys
import os
import json

# Add parent directory for DB imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_database():
    print("[1/3] Checking Database Connection...")
    try:
        from db.schema import get_session, Stock
        session = get_session()
        count = session.query(Stock).count()
        print(f"✅ Database OK: Found {count} symbols in registry.")
        session.close()
        return True
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False

def check_api():
    print("[2/3] Checking API Reachability...")
    try:
        response = requests.get("http://localhost:8000/api/model-status", timeout=5)
        if response.status_code == 200:
            print("✅ API OK: Gateway is responding on port 8000.")
            return True
        else:
            print(f"⚠️ API Warning: Received status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Error: Connection failed. Ensure 'run_app.py' is active.")
        return False

def check_models():
    print("[3/3] Checking AI Model Readiness...")
    metadata_path = "models/checkpoints/metadata.json"
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            meta = json.load(f)
            print(f"✅ AI OK: Models ready (Last training: {meta.get('last_train', 'Unknown')})")
            return True
    else:
        print("⚠️ AI Warning: Metadata not found. Models may still be initializing.")
        return False

if __name__ == "__main__":
    print("=== MarketIntel AI Health Audit ===\n")
    db = check_database()
    api = check_api()
    ai = check_models()
    
    print("\n" + "="*35)
    if all([db, api, ai]):
        print("🚀 SYSTEM STATUS: ALL SYSTEMS NOMINAL")
    else:
        print("⚠️ SYSTEM STATUS: ATTENTION REQUIRED")
    print("="*35)
