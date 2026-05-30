import os
import sys
import threading
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

# Import from schema and preprocess
sys.path.append(os.getcwd())
from db.schema import get_session, Stock, HistoricalPrice
from models.preprocess import calculate_technical_indicators
from backtest_reports.rl_trading_agent import QNetwork, TradingEnv, DQNAgent

# In-memory tracking of currently training stocks
TRAINING_STATUS = {}
TRAINING_LOCK = threading.Lock()

def train_dqn_in_background(ticker: str):
    """
    Background worker to train the DQN agent for a specific ticker on all available history.
    """
    global TRAINING_STATUS
    try:
        session = get_session()
        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock:
            session.close()
            with TRAINING_LOCK:
                TRAINING_STATUS[ticker] = "FAILED"
            return
            
        # Load all history
        prices_df = pd.read_sql(
            session.query(HistoricalPrice).filter_by(
                stock_id=stock.id, 
                exchange="NSE"
            ).order_by(HistoricalPrice.date.asc()).statement,
            session.bind
        )
        session.close()
        
        if len(prices_df) < 150:
            with TRAINING_LOCK:
                TRAINING_STATUS[ticker] = "FAILED"
            return
            
        # Calculate technical indicators
        prices_df = calculate_technical_indicators(prices_df)
        prices_df = prices_df.dropna(subset=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']).reset_index(drop=True)
        
        # Train on the entire available dataset
        env = TradingEnv(prices_df)
        agent = DQNAgent(state_dim=11, action_space=4)
        
        epochs = 30
        step_count = 0
        for epoch in range(epochs):
            state = env.reset()
            done = False
            while not done:
                action = agent.act(state)
                next_state, reward, done, info = env.step(action)
                agent.memory.push(state, action, reward, next_state, done)
                state = next_state
                
                step_count += 1
                if step_count % 4 == 0:
                    agent.train_step()
                    
            if epoch % 5 == 0:
                agent.target_net.load_state_dict(agent.policy_net.state_dict())
                
        # Save model weights to production checkpoints/rl directory
        os.makedirs('models/checkpoints/rl', exist_ok=True)
        torch.save(agent.policy_net.state_dict(), f'models/checkpoints/rl/{ticker}_dqn.pth')
        
        with TRAINING_LOCK:
            TRAINING_STATUS[ticker] = "SUCCESS"
            
    except Exception as e:
        print(f"Error training DQN background task for {ticker}: {e}")
        with TRAINING_LOCK:
            TRAINING_STATUS[ticker] = "FAILED"

def get_rl_signal(ticker: str) -> dict:
    """
    Retrieves the live prediction signal from the DQN RL model.
    Spawns background training on-demand if the model is missing or stale.
    """
    global TRAINING_STATUS
    
    model_dir = 'models/checkpoints/rl'
    model_path = os.path.join(model_dir, f'{ticker}_dqn.pth')
    
    # 1. Check if model exists
    if not os.path.exists(model_path):
        with TRAINING_LOCK:
            status = TRAINING_STATUS.get(ticker, "IDLE")
            
        if status != "TRAINING":
            # Start background training
            with TRAINING_LOCK:
                TRAINING_STATUS[ticker] = "TRAINING"
            thread = threading.Thread(target=train_dqn_in_background, args=(ticker,), daemon=True)
            thread.start()
            
        return {
            "signal": "PROCESSING",
            "confidence": 0.0,
            "status": "Training DQN in background on-demand. Please refresh in 10-15 seconds."
        }
        
    # 2. Check if the model is stale (i.e. modified on a previous day)
    file_mtime = os.path.getmtime(model_path)
    file_date = datetime.date.fromtimestamp(file_mtime)
    today_date = datetime.date.today()
    
    if file_date < today_date:
        with TRAINING_LOCK:
            status = TRAINING_STATUS.get(ticker, "IDLE")
            
        if status != "TRAINING":
            # Trigger silent background retraining to update weights for tomorrow,
            # but do NOT block the user today (we will serve using the existing model).
            with TRAINING_LOCK:
                TRAINING_STATUS[ticker] = "TRAINING"
            thread = threading.Thread(target=train_dqn_in_background, args=(ticker,), daemon=True)
            thread.start()
            
    # 3. Run live inference on the latest price and indicators
    session = get_session()
    try:
        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock:
            return {"error": "Ticker not found"}
            
        # Get latest 150 days of history for indicators
        prices_df = pd.read_sql(
            session.query(HistoricalPrice).filter_by(
                stock_id=stock.id, 
                exchange="NSE"
            ).order_by(HistoricalPrice.date.desc()).limit(150).statement,
            session.bind
        ).iloc[::-1].reset_index(drop=True)
        
        if len(prices_df) < 100:
            return {"error": "Insufficient historical data for inference."}
            
        # Calculate technical indicators
        prices_df = calculate_technical_indicators(prices_df)
        prices_df = prices_df.dropna(subset=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']).reset_index(drop=True)
        
        # Build current state vector (latest row)
        latest_row = prices_df.iloc[-1]
        close = float(latest_row['close'])
        rsi = float(latest_row.get('RSI_14', 50)) / 100.0
        adx = float(latest_row.get('ADX_14', 20)) / 100.0
        macd = float(latest_row.get('MACD', 0)) / close
        atr = float(latest_row.get('ATR_14', close * 0.02)) / close
        
        in_long = 0.0
        in_short = 0.0
        days_held_norm = 0.0
        current_return = 0.0
        
        sma20_rel = (close - float(latest_row.get('SMA_20', close))) / close
        sma50_rel = (close - float(latest_row.get('SMA_50', close))) / close
        
        state = np.array([
            rsi, adx, macd, atr, in_long, in_short, 
            days_held_norm, current_return, sma20_rel, sma50_rel,
            1.0 if latest_row.get('close') > latest_row.get('Typical_Price', latest_row.get('close')) else 0.0
        ], dtype=np.float32)
        
        # Run inference using pre-trained network
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = QNetwork(state_dim=11, action_dim=4).to(device)
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
        
        state_t = torch.FloatTensor(state).to(device)
        with torch.no_grad():
            q_values = model(state_t).squeeze(0)  # shape: [4]
            # Multiply Q-values by 100.0 to scale the softmax distribution and give realistic confidence
            probs = torch.softmax(q_values * 100.0, dim=0).cpu().numpy()
            action = int(torch.argmax(q_values).item())
            
        # Map Action code to recommendation
        signal_map = {
            0: "HOLD",
            1: "BUY",
            2: "SELL",
            3: "EXIT"
        }
        signal = signal_map.get(action, "HOLD")
        confidence = float(probs[action])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "status": "Ready" if file_date == today_date else "Updating in background"
        }
    finally:
        session.close()
