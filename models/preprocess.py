import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import torch

def calculate_technical_indicators(df):
    """
    Calculate an Advanced Industrial Technical Suite for the dataframe.
    """
    # Ensure data is sorted
    df = df.sort_values('date')

    # 1. Moving Averages
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    
    # 2. RSI (14) - Relative Strength Index
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # 3. MACD (Moving Average Convergence Divergence)
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # 4. Bollinger Bands (20, 2)
    df['BB_Mid'] = df['close'].rolling(window=20).mean()
    df['BB_Std'] = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    
    # 5. ATR (Average True Range) - Volatility
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR_14'] = true_range.rolling(14).mean()

    # 6. VWAP (Volume Weighted Average Price) - Benchmark
    # Simple calculation for daily data (Typical Price * Volume / Total Volume)
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['volume']).cumsum() / df['volume'].cumsum()
    
    return df

def prepare_lstm_data(df, window_size=60, feature_cols=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']):
    """
    Prepare sequences for LSTM.
    """
    # Fill any NaNs from technical indicators
    df = df.ffill().bfill()
    
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df[feature_cols])
    
    X, y = [], []
    for i in range(window_size, len(scaled_data)):
        X.append(scaled_data[i-window_size:i])
        y.append(scaled_data[i, 0]) # Predicting 'close' price
        
    return np.array(X), np.array(y), scaler

def to_torch(X, y):
    """
    Convert numpy arrays to torch tensors.
    """
    X_tensor = torch.from_numpy(X).type(torch.Tensor)
    y_tensor = torch.from_numpy(y).type(torch.Tensor).view(-1, 1)
    return X_tensor, y_tensor
