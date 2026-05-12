"""
MarketIntel AI: Global Service Orchestrator
===========================================

This is the primary entry point for the MarketIntel AI ecosystem. It 
automatically initializes the database, performs historical data syncs, 
and spawns the backend API, frontend dashboard, and real-time ingestion 
daemons as separate processes.
"""
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
    """
    Verifies database integrity and performs automated multi-layer backfills.
    """
    print("[CHECK] Checking database state...")
    from db.schema import get_session, HistoricalPrice, Stock, HistoricalFundamentals
    session = get_session()
    try:
        # 1. Check if stocks exist
        stock_count = session.query(Stock).count()
        if stock_count == 0:
            print("[NEW] No stocks found. Discovering market symbols...")
            subprocess.run([PYTHON_EXE, "ingestion/discover_symbols.py"], check=True)
        
        # 2. Update Price History
        hist_count = session.query(HistoricalPrice).count()
        if hist_count == 0:
            print("[WARN] Price history empty! Starting 5-year backfill...")
            subprocess.run([PYTHON_EXE, "ingestion/backfill_history.py"], check=True)
        else:
            print("[DELTA] Syncing missing days...")
            subprocess.run([PYTHON_EXE, "ingestion/delta_update.py"], check=True)

        # 3. ADVANCED: Historical Fundamental Bridge
        fund_count = session.query(HistoricalFundamentals).count()
        if fund_count < 500000: # Threshold for 'deep' history
            print("[ADVANCED] Fundamental history depth is low. Patching 5-year bridge in background...")
            # Run this in background to avoid blocking app start
            subprocess.Popen([PYTHON_EXE, "ingestion/backfill_fundamentals.py", "--bulk", "--limit", "100"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
    finally:
        session.close()

def start_services():
    """
    Spawns the full MarketIntel AI ecosystem.
    """
    processes = []
    print("[START] Initializing Global Orchestrator...")

    # 1. Database Layer
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    time.sleep(10)

    # 2. API Layer (Port 8000)
    print("[API] Starting Backend Engine...")
    processes.append(subprocess.Popen([PYTHON_EXE, "api/main.py"], creationflags=subprocess.CREATE_NEW_CONSOLE))
    time.sleep(2)
    
    # 3. UI Layer (Port 3000)
    print("[DASHBOARD] Starting UI Terminal...")
    dashboard_path = os.path.join(os.getcwd(), "dashboard")
    processes.append(subprocess.Popen("npm run dev", cwd=dashboard_path, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE))

    # 4. Intelligence & Ingestion Layer
    print("[INIT] Running Data Sync...")
    check_db_and_backfill()

    print("[POLL] Starting Real-time Price Polling...")
    processes.append(subprocess.Popen([PYTHON_EXE, "ingestion/poll_prices.py"], creationflags=subprocess.CREATE_NEW_CONSOLE))

    print("[SENTIMENT] Starting News Aggregator...")
    processes.append(subprocess.Popen([PYTHON_EXE, "ingestion/news_aggregator.py"], creationflags=subprocess.CREATE_NEW_CONSOLE))

    # 5. AUTONOMOUS LEARNER (The "Brain")
    print("[BRAIN] Starting Autonomous Learner & Auditor...")
    processes.append(subprocess.Popen([PYTHON_EXE, "intelligence/auto_learner.py"], creationflags=subprocess.CREATE_NEW_CONSOLE))

    print("\n" + "="*50)
    print("MARKETINTEL AI IS LIVE")
    print("="*50)
    print(f"Dashboard: http://localhost:3000")
    print(f"API Docs:  http://localhost:8000/docs")
    print("="*50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping orchestrator...")
        for p in processes: p.terminate()

if __name__ == "__main__":
    start_services()
