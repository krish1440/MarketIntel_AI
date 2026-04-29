import subprocess
import time
import sys
import os
import signal

# Ensure we use the virtual environment's python
PYTHON_EXE = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    # Fallback to sys.executable if venv is missing
    PYTHON_EXE = sys.executable

def check_db_and_backfill():
    print("[CHECK] Checking database state...")
    from db.schema import get_session, HistoricalPrice, Stock
    session = get_session()
    try:
        # 1. Check if stocks exist
        stock_count = session.query(Stock).count()
        if stock_count == 0:
            print("[NEW] No stocks found in database. Discovering full market symbols...")
            subprocess.run([PYTHON_EXE, "ingestion/discover_symbols.py"], check=True)
            print(f"[SUCCESS] Market discovery complete.")
        
        # 2. Update price history (Delta Update)
        hist_count = session.query(HistoricalPrice).count()
        if hist_count == 0:
            print("[WARN] Historical data is empty! Starting whole-market batch backfill...")
            subprocess.run([PYTHON_EXE, "ingestion/backfill_history.py"], check=True)
            print("[SUCCESS] Full backfill complete.")
        else:
            print(f"[DELTA] Syncing missing days since last run...")
            subprocess.run([PYTHON_EXE, "ingestion/delta_update.py"], check=True)
            print("[SUCCESS] Market data is now up to date.")
            
    except Exception as e:
        print(f"[ERROR] Error during initialization: {e}")
    finally:
        session.close()

def start_services():
    processes = []
    
    print("[START] Starting MarketIntel AI Ecosystem...")

    # 1. Start Database (Docker)
    print("[DOCKER] Starting PostgreSQL via Docker...")
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    
    # Wait for DB to be ready for connections
    print("[WAIT] Waiting for Database to initialize...")
    time.sleep(3)

    # 2. Start Backend API First (So the UI works immediately)
    print("[API] Starting Backend API...")
    api_proc = subprocess.Popen([PYTHON_EXE, "api/main.py"], 
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(api_proc)
    
    # Wait for API port binding
    time.sleep(2)
    
    # 3. Start Frontend Dashboard
    print("[DASHBOARD] Starting Frontend Dashboard...")
    dashboard_path = os.path.join(os.getcwd(), "dashboard")
    front_proc = subprocess.Popen("npm run dev", cwd=dashboard_path, shell=True,
                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(front_proc)

    # 4. NOW run the data sync in the background (Doesn't block the UI)
    print("[SYNC] Initializing background data catch-up...")
    check_db_and_backfill()

    # 5. Start Real-time Services
    print("[POLL] Starting Price Polling Service...")
    poll_proc = subprocess.Popen([PYTHON_EXE, "ingestion/poll_prices.py"], 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(poll_proc)

    # 5. Start News Aggregator
    print("[NEWS] Starting News & Sentiment Aggregator...")
    news_proc = subprocess.Popen([PYTHON_EXE, "ingestion/news_aggregator.py"], 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(news_proc)

    # 6. Start Frontend Dashboard
    print("[DASHBOARD] Starting Frontend Dashboard...")
    # Change directory for npm
    dashboard_path = os.path.join(os.getcwd(), "dashboard")
    front_proc = subprocess.Popen("npm run dev", cwd=dashboard_path, shell=True,
                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(front_proc)

    print("\n[SUCCESS] ALL SERVICES RUNNING!")
    print("[LINK] Dashboard: http://localhost:3000")
    print("[LINK] API Docs:  http://localhost:8000/docs")
    print("\nKeep this window open. Closing it will NOT stop the background consoles.")
    print("To stop everything, you will need to close the individual windows.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping orchestrator...")

if __name__ == "__main__":
    start_services()
