import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import torch

def calculate_technical_indicators(df):
    """
    Calculate basic technical indicators for the dataframe.
    """
    # SMA 20
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    
    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # MACD (12, 26, 9)
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.dropna()

def prepare_lstm_data(df, window_size=60, feature_cols=['close', 'SMA_20', 'RSI_14', 'MACD']):
    """
    Prepare sequences for LSTM.
    """
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
