import sys
import os
import random
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque

# Add parent directory to path to import db schema
sys.path.append(os.getcwd())
from db.schema import get_session, Stock, HistoricalPrice
from models.preprocess import calculate_technical_indicators

# Define PyTorch Q-Network
class QNetwork(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 32)
        self.out = nn.Linear(32, action_dim)
        
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x):
        # Handle batch size of 1 for inference
        if x.dim() == 1:
            x = x.unsqueeze(0)
            
        h = self.relu(self.fc1(x))
        h = self.dropout(self.relu(self.fc2(h)))
        h = self.relu(self.fc3(h))
        return self.out(h)

# Experience Replay Buffer
class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
        
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
        
    def sample(self, batch_size):
        state, action, reward, next_state, done = zip(*random.sample(self.buffer, batch_size))
        return (torch.FloatTensor(np.array(state)),
                torch.LongTensor(action),
                torch.FloatTensor(reward),
                torch.FloatTensor(np.array(next_state)),
                torch.FloatTensor(done))
                
    def __len__(self):
        return len(self.buffer)

# Trading Environment Simulator
class TradingEnv:
    def __init__(self, df, initial_capital=100000.0):
        self.df = df.reset_index(drop=True)
        self.initial_capital = initial_capital
        self.action_space = 4  # 0: HOLD, 1: LONG, 2: SHORT, 3: EXIT
        self.reset()
        
    def reset(self):
        self.current_step = 60  # Start after indicators warm up (warmup window = 60 days)
        self.capital = self.initial_capital
        self.shares = 0
        self.position_type = None  # "LONG", "SHORT", or None
        self.entry_price = 0.0
        self.highest_price = 0.0
        self.lowest_price = 0.0
        self.entry_atr = 0.0
        self.days_held = 0
        self.portfolio_value_history = [self.initial_capital]
        self.trades_history = []
        return self._get_state()
        
    def _get_state(self):
        row = self.df.iloc[self.current_step]
        
        # State representation (11 features)
        close = float(row['close'])
        rsi = float(row.get('RSI_14', 50)) / 100.0
        adx = float(row.get('ADX_14', 20)) / 100.0
        macd = float(row.get('MACD', 0)) / close
        atr = float(row.get('ATR_14', close * 0.02)) / close
        
        # Position features
        in_long = 1.0 if self.position_type == "LONG" else 0.0
        in_short = 1.0 if self.position_type == "SHORT" else 0.0
        days_held_norm = self.days_held / 30.0
        
        current_return = 0.0
        if self.position_type == "LONG" and self.entry_price > 0:
            current_return = (close - self.entry_price) / self.entry_price
        elif self.position_type == "SHORT" and self.entry_price > 0:
            current_return = (self.entry_price - close) / self.entry_price
            
        # Price relation to SMAs
        sma20_rel = (close - float(row.get('SMA_20', close))) / close
        sma50_rel = (close - float(row.get('SMA_50', close))) / close
        
        state = np.array([
            rsi, adx, macd, atr, in_long, in_short, 
            days_held_norm, current_return, sma20_rel, sma50_rel,
            1.0 if row.get('close') > row.get('Typical_Price', row.get('close')) else 0.0
        ], dtype=np.float32)
        return state

    def step(self, action):
        row = self.df.iloc[self.current_step]
        current_price = float(row['close'])
        atr = float(row.get('ATR_14', current_price * 0.02))
        
        # Default action detail
        action_detail = "HOLD"
        
        # Check broad trend rules (ADX multiplier)
        adx = float(row.get('ADX_14', 20))
        atr_multiplier = 2.2 if adx > 25 else 1.3
        
        # 1. Evaluate Trailing Stops & Exits on Active Positions
        exited = False
        if self.position_type == "LONG" and self.shares > 0:
            self.days_held += 1
            self.highest_price = max(self.highest_price, current_price)
            trailing_stop = self.highest_price - (atr_multiplier * self.entry_atr)
            take_profit = self.entry_price + (2.5 * self.entry_atr)
            
            # Stop-Loss
            if current_price < trailing_stop:
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_SL"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            # Take-Profit
            elif current_price >= take_profit:
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_TP"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            # Max Days Exit
            elif self.days_held >= 12 and current_price < self.entry_price:
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_TIME"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
                
        elif self.position_type == "SHORT" and self.shares > 0:
            self.days_held += 1
            self.lowest_price = min(self.lowest_price, current_price)
            trailing_stop = self.lowest_price + (1.2 * self.entry_atr)  # Tighter short protection
            take_profit = self.entry_price - (2.5 * self.entry_atr)
            
            # Stop-Loss
            if current_price > trailing_stop:
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_SL_SHORT"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            # Take-Profit
            elif current_price <= take_profit:
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_TP_SHORT"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            # Max Days Exit
            elif self.days_held >= 12 and current_price > self.entry_price:
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_TIME_SHORT"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True

        # 2. Process Agent-Driven Decisions (only if in cash and didn't exit today)
        if (self.position_type is None) and (not exited):
            if action == 1 and self.capital >= current_price:  # BUY / LONG
                shares_to_buy = int(self.capital // current_price)
                if shares_to_buy > 0:
                    self.shares = shares_to_buy
                    self.capital -= self.shares * current_price
                    self.position_type = "LONG"
                    self.entry_price = current_price
                    self.highest_price = current_price
                    self.entry_atr = atr
                    self.days_held = 0
                    action_detail = "BUY"
                    self.trades_history.append((self.current_step, "BUY", current_price))
                    
            elif action == 2 and self.capital >= current_price:  # SHORT
                shares_to_short = int(self.capital // current_price)
                if shares_to_short > 0:
                    self.shares = shares_to_short
                    self.position_type = "SHORT"
                    self.entry_price = current_price
                    self.lowest_price = current_price
                    self.entry_atr = atr
                    self.days_held = 0
                    action_detail = "SHORT"
                    self.trades_history.append((self.current_step, "SHORT", current_price))
                    
        elif action == 3 and self.shares > 0 and (not exited):  # EXIT
            if self.position_type == "LONG":
                self.capital += self.shares * current_price
            elif self.position_type == "SHORT":
                self.capital += self.shares * (self.entry_price - current_price)
            action_detail = "COVER/SELL"
            self.trades_history.append((self.current_step, "EXIT", current_price))
            self.shares = 0
            self.position_type = None
            self.days_held = 0

        # Calculate portfolio value
        if self.position_type == "LONG":
            portfolio_value = self.capital + (self.shares * current_price)
        elif self.position_type == "SHORT":
            portfolio_value = self.capital + (self.shares * (self.entry_price - current_price))
        else:
            portfolio_value = self.capital
            
        # Reward function: Sharpe-ratio equivalent (Return relative to volatility)
        prev_value = self.portfolio_value_history[-1]
        daily_return = (portfolio_value - prev_value) / prev_value
        
        # Penalize holding flat cash when there are market moves (to push agent to trade)
        cash_penalty = -0.0001 if self.position_type is None else 0.0
        # Penalize deep drawdowns
        drawdown = (portfolio_value - self.initial_capital) / self.initial_capital
        drawdown_penalty = -0.005 if drawdown < -0.1 else 0.0
        
        reward = daily_return + cash_penalty + drawdown_penalty
        
        # Advance step
        self.portfolio_value_history.append(portfolio_value)
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        
        next_state = self._get_state() if not done else np.zeros_like(self._get_state())
        return next_state, reward, done, {"value": portfolio_value, "action": action_detail}

# DQN Agent
class DQNAgent:
    def __init__(self, state_dim, action_space):
        self.state_dim = state_dim
        self.action_space = action_space
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.996
        self.batch_size = 64
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy_net = QNetwork(state_dim, action_space).to(self.device)
        self.target_net = QNetwork(state_dim, action_space).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=0.001)
        self.memory = ReplayBuffer()
        
    def act(self, state):
        if random.random() < self.epsilon:
            return random.randrange(self.action_space)
        state_t = torch.FloatTensor(state).to(self.device)
        with torch.no_grad():
            q_values = self.policy_net(state_t)
            return torch.argmax(q_values).item()
            
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0
            
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        
        # Current Q values
        q_values = self.policy_net(states)
        state_action_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Target Q values
        with torch.no_grad():
            next_q_values = self.target_net(next_states)
            max_next_q_values = torch.max(next_q_values, dim=1)[0]
            expected_state_action_values = rewards + (self.gamma * max_next_q_values * (1 - dones))
            
        # Huber Loss
        loss_fn = nn.SmoothL1Loss()
        loss = loss_fn(state_action_values, expected_state_action_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        return loss.item()

def run_rl_experiment(ticker="TCS"):
    print(f"\n" + "="*50)
    print(f"LOADING STOCK: {ticker} FOR REINFORCEMENT LEARNING")
    print("="*50)
    
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock:
        print("Error: Stock not found.")
        session.close()
        return
        
    # Ingest historical prices
    prices_df = pd.read_sql(
        session.query(HistoricalPrice).filter_by(stock_id=stock.id, exchange="NSE").order_by(HistoricalPrice.date.asc()).statement,
        session.bind
    )
    session.close()
    
    if len(prices_df) < 200:
        print("Error: Insufficient historical prices.")
        return
        
    # Calculate indicators
    prices_df = calculate_technical_indicators(prices_df)
    prices_df = prices_df.dropna(subset=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']).reset_index(drop=True)
    
    # Train / Test Split (OOS Test starts at 2025-11-01)
    split_date = datetime.date(2025, 11, 1)
    train_df = prices_df[prices_df['date'] < split_date]
    test_df = prices_df[prices_df['date'] >= split_date]
    
    print(f"Dataset Split: {len(train_df)} Train rows, {len(test_df)} Test (OOS) rows.")
    
    # Initialize environment and agent
    env = TradingEnv(train_df)
    state_dim = 11
    action_space = 4
    agent = DQNAgent(state_dim, action_space)
    
    # Training Loop
    epochs = 40
    print("\nStarting RL Agent training loop...")
    for epoch in range(epochs):
        state = env.reset()
        total_reward = 0
        done = False
        losses = []
        
        while not done:
            action = agent.act(state)
            next_state, reward, done, info = env.step(action)
            agent.memory.push(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward
            
            # Perform optimization step
            loss = agent.train_step()
            if loss > 0:
                losses.append(loss)
                
        # Sync target network periodically
        if epoch % 5 == 0:
            agent.target_net.load_state_dict(agent.policy_net.state_dict())
            
        avg_loss = sum(losses)/len(losses) if losses else 0.0
        final_val = env.portfolio_value_history[-1]
        print(f"Epoch {epoch+1:02d}/{epochs} | Avg Loss: {avg_loss:.5f} | Total Reward: {total_reward:.2f} | Final Portfolio: Rs. {final_val:,.2f} | Epsilon: {agent.epsilon:.2f}")
        
    # Evaluate Agent on Out-of-Sample Test set
    print("\n" + "="*50)
    print(f"EVALUATING TRAINED RL AGENT OUT-OF-SAMPLE (OOS)")
    print("="*50)
    
    test_env = TradingEnv(test_df)
    agent.epsilon = 0.0  # Fully greedy actions during evaluation
    
    state = test_env.reset()
    done = False
    action_logs = []
    
    while not done:
        action = agent.act(state)
        # Record the date
        date_str = test_env.df.iloc[test_env.current_step]['date'].isoformat()
        next_state, reward, done, info = test_env.step(action)
        state = next_state
        
        action_logs.append({
            "Date": date_str,
            "Price": test_env.df.iloc[test_env.current_step - 1]['close'],
            "DQN_Action": info["action"],
            "Portfolio_Value": info["value"]
        })
        
    final_oos_val = test_env.portfolio_value_history[-1]
    oos_return = ((final_oos_val / 100000.0) - 1) * 100
    
    # Save log to CSV
    os.makedirs('backtest_reports/results', exist_ok=True)
    df_logs = pd.DataFrame(action_logs)
    df_logs.to_csv(f'backtest_reports/results/{ticker}_rl_oos_evaluation.csv', index=False)
    
    # Calculate Sharpe ratio equivalent
    val_series = pd.Series(test_env.portfolio_value_history)
    daily_pct = val_series.pct_change().dropna()
    std_dev = daily_pct.std()
    sharpe = (daily_pct.mean() / std_dev * np.sqrt(252)) if std_dev > 0 else 0.0
    
    print(f"Initial Value:  Rs. 100,000.00")
    print(f"Final Value:    Rs. {final_oos_val:,.2f}")
    print(f"OOS Net Return: {oos_return:.2f}%")
    print(f"Annual Sharpe:  {sharpe:.2f}")
    print(f"Total Trades:   {len(test_env.trades_history)}")
    print(f"Detailed logs saved to: backtest_reports/results/{ticker}_rl_oos_evaluation.csv")
    print("="*50)

if __name__ == "__main__":
    ticker = "TCS"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    run_rl_experiment(ticker)
