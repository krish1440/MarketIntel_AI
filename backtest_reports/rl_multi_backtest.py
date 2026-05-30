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

# Define PyTorch Q-Network (without BatchNorm to avoid batch-size-1 training-mode issues)
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
        if x.dim() == 1:
            x = x.unsqueeze(0)
        h = self.relu(self.fc1(x))
        h = self.dropout(self.relu(self.fc2(h)))
        h = self.relu(self.fc3(h))
        return self.out(h)

# Replay Buffer
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

# Environment Simulator
class TradingEnv:
    def __init__(self, df, initial_capital=100000.0):
        self.df = df.reset_index(drop=True)
        self.initial_capital = initial_capital
        self.action_space = 4  # 0: HOLD, 1: BUY, 2: SHORT, 3: EXIT
        self.reset()
        
    def reset(self):
        self.current_step = 60  # Warmup window
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
        close = float(row['close'])
        rsi = float(row.get('RSI_14', 50)) / 100.0
        adx = float(row.get('ADX_14', 20)) / 100.0
        macd = float(row.get('MACD', 0)) / close
        atr = float(row.get('ATR_14', close * 0.02)) / close
        
        in_long = 1.0 if self.position_type == "LONG" else 0.0
        in_short = 1.0 if self.position_type == "SHORT" else 0.0
        days_held_norm = self.days_held / 30.0
        
        current_return = 0.0
        if self.position_type == "LONG" and self.entry_price > 0:
            current_return = (close - self.entry_price) / self.entry_price
        elif self.position_type == "SHORT" and self.entry_price > 0:
            current_return = (self.entry_price - close) / self.entry_price
            
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
        
        action_detail = "HOLD"
        adx = float(row.get('ADX_14', 20))
        atr_multiplier = 2.2 if adx > 25 else 1.3
        
        exited = False
        if self.position_type == "LONG" and self.shares > 0:
            self.days_held += 1
            self.highest_price = max(self.highest_price, current_price)
            trailing_stop = self.highest_price - (atr_multiplier * self.entry_atr)
            take_profit = self.entry_price + (2.5 * self.entry_atr)
            
            if current_price < trailing_stop:
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_SL"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif current_price >= take_profit:
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_TP"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
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
            trailing_stop = self.lowest_price + (1.2 * self.entry_atr)
            take_profit = self.entry_price - (2.5 * self.entry_atr)
            
            if current_price > trailing_stop:
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_SL_SHORT"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif current_price <= take_profit:
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_TP_SHORT"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif self.days_held >= 12 and current_price > self.entry_price:
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_TIME_SHORT"
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True

        if (self.position_type is None) and (not exited):
            if action == 1 and self.capital >= current_price:
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
                    
            elif action == 2 and self.capital >= current_price:
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
                    
        elif action == 3 and self.shares > 0 and (not exited):
            if self.position_type == "LONG":
                self.capital += self.shares * current_price
            elif self.position_type == "SHORT":
                self.capital += self.shares * (self.entry_price - current_price)
            action_detail = "COVER/SELL"
            self.trades_history.append((self.current_step, "EXIT", current_price))
            self.shares = 0
            self.position_type = None
            self.days_held = 0

        if self.position_type == "LONG":
            portfolio_value = self.capital + (self.shares * current_price)
        elif self.position_type == "SHORT":
            portfolio_value = self.capital + (self.shares * (self.entry_price - current_price))
        else:
            portfolio_value = self.capital
            
        prev_value = self.portfolio_value_history[-1]
        daily_return = (portfolio_value - prev_value) / prev_value
        
        cash_penalty = -0.0001 if self.position_type is None else 0.0
        drawdown = (portfolio_value - self.initial_capital) / self.initial_capital
        drawdown_penalty = -0.005 if drawdown < -0.1 else 0.0
        
        reward = daily_return + cash_penalty + drawdown_penalty
        
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
        
        q_values = self.policy_net(states)
        state_action_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        with torch.no_grad():
            next_q_values = self.target_net(next_states)
            max_next_q_values = torch.max(next_q_values, dim=1)[0]
            expected_state_action_values = rewards + (self.gamma * max_next_q_values * (1 - dones))
            
        loss_fn = nn.SmoothL1Loss()
        loss = loss_fn(state_action_values, expected_state_action_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        return loss.item()

def run_backtest_for_ticker(ticker, train_start, train_end, test_start, test_end, epochs=30):
    session = get_session()
    stock = session.query(Stock).filter_by(ticker=ticker).first()
    if not stock:
        session.close()
        return None
        
    # Ingest historical prices covering both train and test periods
    prices_df = pd.read_sql(
        session.query(HistoricalPrice).filter(
            HistoricalPrice.stock_id == stock.id,
            HistoricalPrice.exchange == "NSE",
            HistoricalPrice.date >= train_start,
            HistoricalPrice.date <= test_end
        ).order_by(HistoricalPrice.date.asc()).statement,
        session.bind
    )
    session.close()
    
    if len(prices_df) < 200:
        return None
        
    # Calculate technical indicators on the whole dataframe first (non-lookahead, row-by-row functions only)
    prices_df = calculate_technical_indicators(prices_df)
    prices_df = prices_df.dropna(subset=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']).reset_index(drop=True)
    
    # Split into train and test purely based on dates
    train_df = prices_df[(prices_df['date'] >= train_start) & (prices_df['date'] <= train_end)].reset_index(drop=True)
    test_df = prices_df[(prices_df['date'] >= test_start) & (prices_df['date'] <= test_end)].reset_index(drop=True)
    
    if len(train_df) < 100 or len(test_df) < 20:
        return None
        
    # Train DQN agent
    env = TradingEnv(train_df)
    agent = DQNAgent(state_dim=11, action_space=4)
    
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
            
    # Save the trained model model weights to backtest_reports/models/
    os.makedirs('backtest_reports/models', exist_ok=True)
    torch.save(agent.policy_net.state_dict(), f'backtest_reports/models/{ticker}_dqn.pth')
            
    # Evaluate DQN agent on test set (OOS)
    test_env = TradingEnv(test_df)
    agent.epsilon = 0.0  # Greedy evaluation
    state = test_env.reset()
    done = False
    
    while not done:
        action = agent.act(state)
        next_state, reward, done, info = test_env.step(action)
        state = next_state
        
    final_rl_val = test_env.portfolio_value_history[-1]
    rl_return = ((final_rl_val / 100000.0) - 1) * 100
    
    # Calculate Sharpe ratio equivalent
    val_series = pd.Series(test_env.portfolio_value_history)
    daily_pct = val_series.pct_change().dropna()
    std_dev = daily_pct.std()
    sharpe = (daily_pct.mean() / std_dev * np.sqrt(252)) if std_dev > 0 else 0.0
    
    # Calculate passive Buy & Hold return on the test set
    start_close = float(test_df.iloc[0]['close'])
    end_close = float(test_df.iloc[-1]['close'])
    bh_return = ((end_close / start_close) - 1) * 100
    
    return {
        "ticker": ticker,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "rl_return": rl_return,
        "bh_return": bh_return,
        "trades": len(test_env.trades_history),
        "sharpe": sharpe,
        "final_value": final_rl_val
    }

if __name__ == "__main__":
    # Define splits: 4 years training, 1 year testing
    test_end = datetime.date(2026, 5, 29)
    test_start = datetime.date(2025, 5, 29)
    train_end = datetime.date(2025, 5, 28)
    train_start = datetime.date(2021, 5, 29)
    
    # Chunk of 10 key stocks selected from user's Nifty 50 list
    tickers = ["TCS", "RELIANCE", "INFY", "HDFCBANK", "ICICIBANK", "ADANIENT", "SBIN", "LT", "ITC", "BHARTIRTIL"]
    
    print("="*60)
    print("RUNNING MULTI-STOCK DQN RL BACKTEST COMPARISON")
    print(f"Train period: {train_start} to {train_end}")
    print(f"Test period (OOS): {test_start} to {test_end}")
    print("="*60)
    
    results = []
    for ticker in tickers:
        print(f"Processing {ticker:10s} ... ", end="", flush=True)
        try:
            res = run_backtest_for_ticker(ticker, train_start, train_end, test_start, test_end)
            if res:
                results.append(res)
                print(f"DONE | RL OOS Return: {res['rl_return']:.2f}% | B&H Return: {res['bh_return']:.2f}% | Trades: {res['trades']}")
            else:
                print("SKIPPED (Insufficient Data)")
        except Exception as e:
            print(f"FAILED: {e}")
            
    # Output final summary report
    print("\n" + "="*60)
    print("MULTI-STOCK BACKTEST COMPLETE")
    print("="*60)
    
    report_content = []
    report_content.append("# DQN RL Agent vs Buy & Hold Performance Report (1-Year OOS)")
    report_content.append(f"**Training Period**: {train_start} to {train_end} (4 Years)")
    report_content.append(f"**Test Period (OOS)**: {test_start} to {test_end} (1 Year)")
    report_content.append("\n## Summary Table")
    report_content.append("| Ticker | RL Return % | B&H Return % | Outperformance % | Trades | Sharpe | Final Portfolio (RL) |")
    report_content.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
    
    for r in results:
        outperf = r['rl_return'] - r['bh_return']
        report_content.append(
            f"| {r['ticker']} | {r['rl_return']:.2f}% | {r['bh_return']:.2f}% | {outperf:+.2f}% | {r['trades']} | {r['sharpe']:.2f} | Rs. {r['final_value']:,.2f} |"
        )
        
    report_text = "\n".join(report_content)
    
    # Save the report
    os.makedirs('backtest_reports', exist_ok=True)
    with open('backtest_reports/RL_MULTI_STOCK_PERFORMANCE_REPORT.md', 'w') as f:
        f.write(report_text)
        
    print(report_text)
    print("\nReport successfully saved to backtest_reports/RL_MULTI_STOCK_PERFORMANCE_REPORT.md")
