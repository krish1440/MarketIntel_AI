"""
MarketIntel AI: Data Preprocessing & Technical Engine
=====================================================

This module handles the transformation of raw OHLCV price strings into 
advanced technical indicators and scaled tensor arrays suitable for 
deep learning models.
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
try:
    import torch
    HAS_TORCH_PREPROCESS = True
except Exception as e:
    print(f"Warning: torch could not be loaded in preprocess.py: {e}")
    HAS_TORCH_PREPROCESS = False


def calculate_technical_indicators(df):
    """
    Calculates an Advanced Industrial Technical Suite for a given dataframe.

    Injects SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and VWAP into the 
    price history, dropping the reliance on manual or external calculations.

    Args:
        df (pandas.DataFrame): The raw historical price dataset.

    Returns:
        pandas.DataFrame: The augmented dataset containing the new technical columns.
    """
    # Ensure data is sorted
    df = df.sort_values('date')

    # 1. Moving Averages
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    df['SMA_100'] = df['close'].rolling(window=100).mean()
    
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

    # 6. VWAP (Volume Weighted Average Price)
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['volume']).cumsum() / df['volume'].cumsum()
    
    # 7. ADX (Average Directional Index) - Trend Strength
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = np.abs(minus_dm)
    
    tr_14 = true_range.rolling(14).sum()
    plus_di = 100 * (plus_dm.rolling(14).sum() / tr_14)
    minus_di = 100 * (minus_dm.rolling(14).sum() / tr_14)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX_14'] = dx.rolling(14).mean()
    
    # 8. Ichimoku Cloud (Basic)
    high_9 = df['high'].rolling(window=9).max()
    low_9 = df['low'].rolling(window=9).min()
    df['Ichimoku_Tenkan'] = (high_9 + low_9) / 2
    
    high_26 = df['high'].rolling(window=26).max()
    low_26 = df['low'].rolling(window=26).min()
    df['Ichimoku_Kijun'] = (high_26 + low_26) / 2
    
    # 9. Bollinger Band Width
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Mid']
    
    # 10. CCI (Commodity Channel Index)
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(window=20).mean()
    mad_tp = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean())
    df['CCI_20'] = (tp - sma_tp) / (0.015 * mad_tp)
    
    # 11. OBV (On-Balance Volume)
    df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

    return df

def prepare_lstm_data(df, window_size=60, feature_cols=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14']):
    """
    Transforms tabular data into sequential overlapping windows for LSTM training.

    Args:
        df (pandas.DataFrame): The technical-augmented price dataset.
        window_size (int): Number of time steps per sequence.
        feature_cols (list): Specific columns to include in the sequence window.

    Returns:
        tuple: (X sequences array, y target array, MinMaxScaler object)
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
    Converts preprocessed numpy arrays into PyTorch Tensors.

    Args:
        X (numpy.ndarray): The feature sequences.
        y (numpy.ndarray): The target values.

    Returns:
        tuple: (X_tensor, y_tensor) ready for model ingestion.
    """
    if not HAS_TORCH_PREPROCESS:
        return None, None
    X_tensor = torch.from_numpy(X).type(torch.Tensor)
    y_tensor = torch.from_numpy(y).type(torch.Tensor).view(-1, 1)
    return X_tensor, y_tensor

