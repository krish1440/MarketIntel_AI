import subprocess
import time
import sys
import os
import signal

def check_db_and_backfill():
    print("🔍 Checking database state...")
    from db.schema import get_session, HistoricalPrice, Stock
    session = get_session()
    try:
        # 1. Check if stocks exist
        stock_count = session.query(Stock).count()
        if stock_count == 0:
            print("🆕 No stocks found in database. Discovering full market symbols...")
            subprocess.run([sys.executable, "ingestion/discover_symbols.py"], check=True)
            print(f"✅ Market discovery complete.")
        
        # 2. Check if history exists
        hist_count = session.query(HistoricalPrice).count()
        if hist_count == 0:
            print("⚠️ Historical data is empty! Starting whole-market batch backfill...")
            print("💡 Note: This will download 5 years of data for 2,300+ stocks. Please wait.")
            subprocess.run([sys.executable, "ingestion/backfill_history.py"], check=True)
            print("✅ Backfill complete.")
        else:
            print(f"📊 Database already contains {stock_count} stocks and {hist_count} history records.")
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
    finally:
        session.close()

def start_services():
    processes = []
    
    print("🚀 Starting TradeIntellect Ecosystem...")

    # 1. Start Database (Docker)
    print("📦 Starting PostgreSQL via Docker...")
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    
    # Wait for DB to be ready for connections
    print("⏳ Waiting for Database to initialize...")
    time.sleep(5)

    # 2. Check if we need a fresh backfill
    check_db_and_backfill()

    # 3. Start Backend API
    print("📡 Starting Backend API...")
    api_proc = subprocess.Popen([sys.executable, "api/main.py"], 
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(api_proc)
    
    # 4. Start Price Polling
    print("📈 Starting Price Polling Service...")
    poll_proc = subprocess.Popen([sys.executable, "ingestion/poll_prices.py"], 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(poll_proc)

    # 5. Start News Aggregator
    print("📰 Starting News & Sentiment Aggregator...")
    news_proc = subprocess.Popen([sys.executable, "ingestion/news_aggregator.py"], 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(news_proc)

    # 6. Start Frontend Dashboard
    print("🎨 Starting Frontend Dashboard...")
    # Change directory for npm
    dashboard_path = os.path.join(os.getcwd(), "dashboard")
    front_proc = subprocess.Popen("npm run dev", cwd=dashboard_path, shell=True,
                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
    processes.append(front_proc)

    print("\n✅ ALL SERVICES RUNNING!")
    print("🔗 Dashboard: http://localhost:3000")
    print("🔗 API Docs:  http://localhost:8000/docs")
    print("\nKeep this window open. Closing it will NOT stop the background consoles.")
    print("To stop everything, you will need to close the individual windows.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping orchestrator...")

if __name__ == "__main__":
    start_services()
