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
        self.dropout = nn.Dropout(0.2)
        
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
    def __init__(self, df, initial_capital=100000.0, mode="LONG_TERM"):
        self.df = df.reset_index(drop=True)
        self.initial_capital = initial_capital
        self.mode = mode  # "LONG_TERM" or "SHORT_TERM"
        self.action_space = 3  # 0: HOLD, 1: BUY, 2: SHORT
        self.reset()
        
    def reset(self):
        self.current_step = 100  # Warmup window extended to 100 for SMA_100
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
        self.completed_trades_pnl = []
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
        
        state_list = [
            rsi, adx, macd, atr, in_long, in_short, 
            days_held_norm, current_return, sma20_rel, sma50_rel,
            1.0 if row.get('close') > row.get('Typical_Price', row.get('close')) else 0.0
        ]
        
        if self.mode == "LONG_TERM":
            sma100_rel = (close - float(row.get('SMA_100', close))) / close
            bb_width = float(row.get('BB_Width', 0.1))
            state_list.append(sma100_rel)
            state_list.append(bb_width)
            
        return np.array(state_list, dtype=np.float32)

    def step(self, action):
        row = self.df.iloc[self.current_step]
        current_price = float(row['close'])
        date_str = str(row['date']).split(' ')[0] if 'date' in row else str(self.current_step)
        atr = float(row.get('ATR_14', current_price * 0.02))
        
        action_detail = "HOLD"
        adx = float(row.get('ADX_14', 20))
        
        # Mode-specific parameters
        if self.mode == "LONG_TERM":
            atr_multiplier = 2.5 if adx > 25 else 2.0
            tp_multiplier = 4.0
            max_days = 30
        else: # SHORT_TERM
            atr_multiplier = 0.8
            tp_multiplier = 1.2
            max_days = 5
            
        exited = False
        if self.position_type == "LONG" and self.shares > 0:
            self.days_held += 1
            self.highest_price = max(self.highest_price, current_price)
            trailing_stop = self.highest_price - (atr_multiplier * self.entry_atr)
            take_profit = self.entry_price + (tp_multiplier * self.entry_atr)
            
            pnl = (current_price - self.entry_price) * self.shares
            if current_price < trailing_stop:
                self.completed_trades_pnl.append(pnl)
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_SL"
                self.trades_history.append((date_str, action_detail, current_price, pnl))
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif current_price >= take_profit:
                self.completed_trades_pnl.append(pnl)
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_TP"
                self.trades_history.append((date_str, action_detail, current_price, pnl))
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif (self.mode == "LONG_TERM" and self.days_held >= max_days and current_price < self.entry_price) or \
                 (self.mode == "SHORT_TERM" and self.days_held >= max_days):
                self.completed_trades_pnl.append(pnl)
                self.capital += self.shares * current_price
                action_detail = "STOP_EXIT_TIME"
                self.trades_history.append((date_str, action_detail, current_price, pnl))
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
                
        elif self.position_type == "SHORT" and self.shares > 0:
            self.days_held += 1
            self.lowest_price = min(self.lowest_price, current_price)
            trailing_stop = self.lowest_price + (atr_multiplier * self.entry_atr)
            take_profit = self.entry_price - (tp_multiplier * self.entry_atr)
            
            pnl = (self.entry_price - current_price) * self.shares
            if current_price > trailing_stop:
                self.completed_trades_pnl.append(pnl)
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_SL_SHORT"
                self.trades_history.append((date_str, action_detail, current_price, pnl))
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif current_price <= take_profit:
                self.completed_trades_pnl.append(pnl)
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_TP_SHORT"
                self.trades_history.append((date_str, action_detail, current_price, pnl))
                self.shares = 0
                self.position_type = None
                self.days_held = 0
                exited = True
            elif (self.mode == "LONG_TERM" and self.days_held >= max_days and current_price > self.entry_price) or \
                 (self.mode == "SHORT_TERM" and self.days_held >= max_days):
                self.completed_trades_pnl.append(pnl)
                self.capital += self.shares * (self.entry_price - current_price)
                action_detail = "STOP_EXIT_TIME_SHORT"
                self.trades_history.append((date_str, action_detail, current_price, pnl))
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
                    self.trades_history.append((date_str, "BUY", current_price, 0.0))
                    
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
                    self.trades_history.append((date_str, "SHORT", current_price, 0.0))

        if self.position_type == "LONG":
            portfolio_value = self.capital + (self.shares * current_price)
        elif self.position_type == "SHORT":
            portfolio_value = self.capital + (self.shares * (self.entry_price - current_price))
        else:
            portfolio_value = self.capital
            
        prev_value = self.portfolio_value_history[-1]
        daily_return = (portfolio_value - prev_value) / prev_value
        
        cash_penalty = 0.0
        drawdown = (portfolio_value - self.initial_capital) / self.initial_capital
        drawdown_penalty = -0.005 if drawdown < -0.1 else 0.0
        
        # Scale reward by 10x so Q-values diverge more decisively during training
        reward = (daily_return + cash_penalty + drawdown_penalty) * 10.0
        
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
        
        # Add weight_decay to prevent overfitting since we have limited data
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=0.001, weight_decay=1e-4)
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

def run_backtest_for_ticker(ticker, train_start, train_end, test_start, test_end, epochs=100):
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
        
    # Calculate technical indicators
    prices_df = calculate_technical_indicators(prices_df)
    prices_df = prices_df.dropna(subset=['close', 'SMA_100', 'BB_Width', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']).reset_index(drop=True)
    
    # Split into train and test purely based on dates
    train_df = prices_df[(prices_df['date'] >= train_start) & (prices_df['date'] <= train_end)].reset_index(drop=True)
    test_df = prices_df[(prices_df['date'] >= test_start) & (prices_df['date'] <= test_end)].reset_index(drop=True)
    
    if len(train_df) < 100 or len(test_df) < 20:
        return None
        
    start_close = float(test_df.iloc[0]['close'])
    end_close = float(test_df.iloc[-1]['close'])
    bh_return = ((end_close / start_close) - 1) * 100
    
    results_dict = {"ticker": ticker, "bh_return": bh_return}
    trade_log = [f"# Detailed Trade Log: {ticker}"]
    
    os.makedirs('backtest_reports/models', exist_ok=True)
    os.makedirs('backtest_reports/logs', exist_ok=True)
    
    for mode in ["LONG_TERM", "SHORT_TERM"]:
        state_dim = 13 if mode == "LONG_TERM" else 11
        env = TradingEnv(train_df, mode=mode)
        agent = DQNAgent(state_dim=state_dim, action_space=3)
        
        model_path = f'backtest_reports/models/{ticker}_dqn_{mode.lower()}.pth'
        if os.path.exists(model_path):
            agent.policy_net.load_state_dict(torch.load(model_path, map_location=agent.device))
        else:
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
                    
            torch.save(agent.policy_net.state_dict(), model_path)
                
        # Evaluate OOS
        test_env = TradingEnv(test_df, mode=mode)
        agent.epsilon = 0.0
        state = test_env.reset()
        done = False
        
        while not done:
            action = agent.act(state)
            next_state, reward, done, info = test_env.step(action)
            state = next_state
            
        final_rl_val = test_env.portfolio_value_history[-1]
        rl_return = ((final_rl_val / 100000.0) - 1) * 100
        
        completed_pnl = test_env.completed_trades_pnl
        gross_profit = sum([p for p in completed_pnl if p > 0])
        gross_loss = abs(sum([p for p in completed_pnl if p < 0]))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        win_rate = (len([p for p in completed_pnl if p > 0]) / len(completed_pnl) * 100) if len(completed_pnl) > 0 else 0.0
        
        # Add to results
        prefix = "lt" if mode == "LONG_TERM" else "st"
        results_dict[f"{prefix}_return"] = rl_return
        results_dict[f"{prefix}_trades"] = len(test_env.trades_history)
        results_dict[f"{prefix}_win_rate"] = win_rate
        results_dict[f"{prefix}_profit_factor"] = profit_factor
        results_dict[f"{prefix}_final_val"] = final_rl_val
        
        trade_log.append(f"\n## {mode} Strategy")
        trade_log.append(f"**Profit Factor**: {profit_factor:.2f} | **Win Rate**: {win_rate:.1f}% | **Return**: {rl_return:.2f}%")
        trade_log.append("\n| Date | Action | Price | Trade PnL |")
        trade_log.append("| :--- | :--- | :--- | :--- |")
        for t in test_env.trades_history:
            pnl_str = f"+ Rs. {t[3]:.2f}" if t[3] > 0 else (f"- Rs. {abs(t[3]):.2f}" if t[3] < 0 else "-")
            trade_log.append(f"| {t[0]} | {t[1]} | Rs. {t[2]:.2f} | {pnl_str} |")
            
    with open(f"backtest_reports/logs/trades_{ticker}.md", "w") as f:
        f.write("\n".join(trade_log))
        
    return results_dict

if __name__ == "__main__":
    # Define splits: 4 years training, 1 year testing
    test_end = datetime.date(2026, 5, 29)
    test_start = datetime.date(2025, 5, 29)
    train_end = datetime.date(2025, 5, 28)
    train_start = datetime.date(2021, 5, 29)
    
    # Chunk of 50 key stocks (Nifty 50)
    tickers = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", 
        "BEL", "BHARTIARTL", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", 
        "HDFCBANK", "HDFCLIFE", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INFY", "INDIGO", "ITC", "JIOFIN", 
        "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "MAXHEALTH", "NESTLEIND", "NTPC", "ONGC", 
        "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN", "SUNPHARMA", "TCS", "TATACONSUM", 
        "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO"
    ]
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
                print(f"DONE | LT Ret: {res['lt_return']:.2f}% | ST Ret: {res['st_return']:.2f}% | B&H: {res['bh_return']:.2f}%")
            else:
                print("SKIPPED (Insufficient Data)")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"FAILED: {e}")
            
    # Output final summary report
    print("\n" + "="*60)
    print("MULTI-STOCK BACKTEST COMPLETE")
    print("="*60)
    
    report_content = []
    report_content.append("# DQN RL Agent Dual-Mode Performance Report (1-Year OOS)")
    report_content.append(f"**Training Period**: {train_start} to {train_end} (4 Years)")
    report_content.append(f"**Test Period (OOS)**: {test_start} to {test_end} (1 Year)")
    report_content.append("\n## Summary Table")
    report_content.append("| Ticker | LT Return % | ST Return % | B&H Return % | LT Trades | ST Trades | LT WinRate % | ST WinRate % |")
    report_content.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    total_lt_final = 0.0
    total_st_final = 0.0
    initial_total_val = len(results) * 100000.0
    
    for r in results:
        total_lt_final += r['lt_final_val']
        total_st_final += r['st_final_val']
        report_content.append(
            f"| {r['ticker']} | {r['lt_return']:.2f}% | {r['st_return']:.2f}% | {r['bh_return']:.2f}% | {r['lt_trades']} | {r['st_trades']} | {r['lt_win_rate']:.1f}% | {r['st_win_rate']:.1f}% |"
        )
        
    lt_total_return_pct = ((total_lt_final / initial_total_val) - 1) * 100 if initial_total_val > 0 else 0
    st_total_return_pct = ((total_st_final / initial_total_val) - 1) * 100 if initial_total_val > 0 else 0
    
    report_content.append("\n### Portfolio Aggregate Performance")
    report_content.append(f"* **Total Capital Deployed**: Rs. {initial_total_val:,.2f} per mode")
    report_content.append(f"\n#### Long-Term Mode")
    report_content.append(f"* **Total Final Value**: Rs. {total_lt_final:,.2f}")
    report_content.append(f"* **Total Profit / Loss**: Rs. {(total_lt_final - initial_total_val):,.2f} ({lt_total_return_pct:+.2f}%)")
    report_content.append(f"\n#### Short-Term Mode")
    report_content.append(f"* **Total Final Value**: Rs. {total_st_final:,.2f}")
    report_content.append(f"* **Total Profit / Loss**: Rs. {(total_st_final - initial_total_val):,.2f} ({st_total_return_pct:+.2f}%)")
        
    report_text = "\n".join(report_content)
    
    # Save the report
    os.makedirs('backtest_reports', exist_ok=True)
    with open('backtest_reports/RL_MULTI_STOCK_PERFORMANCE_REPORT.md', 'w') as f:
        f.write(report_text)
        
    print(report_text)
    print("\nReport successfully saved to backtest_reports/RL_MULTI_STOCK_PERFORMANCE_REPORT.md")
