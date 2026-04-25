import xgboost as xgb
import pandas as pd
import numpy as np
from db.schema import get_session, HistoricalPrice, NewsArticle
from .preprocess import prepare_lstm_data, calculate_technical_indicators, to_torch
import torch

def generate_fusion_dataset(session, stock_id):
    # 1. Fetch Price Data
    prices = pd.read_sql(session.query(HistoricalPrice).filter_by(stock_id=stock_id).statement, session.bind)
    if len(prices) < 70: return None
    
    prices = calculate_technical_indicators(prices)
    X_lstm, y_lstm, scaler = prepare_lstm_data(prices)
    
    # 2. Fetch News Data
    news = pd.read_sql(session.query(NewsArticle).filter_by(stock_id=stock_id).statement, session.bind)
    
    # 3. Align by Date
    fusion_X, fusion_y = [], []
    
    for i in range(len(X_lstm)):
        current_date = prices.iloc[i + 60]['date'] # The date we are predicting for
        
        # Get sentiment for the 24h prior to this date
        mask = (news['published_at'].dt.date == current_date)
        daily_sent = news.loc[mask, 'sentiment_score'].mean()
        if pd.isna(daily_sent): daily_sent = 0.0
        
        # Target: 1 if close > prev_close, 0 otherwise
        target = 1 if prices.iloc[i + 60]['close'] > prices.iloc[i + 59]['close'] else 0
        
        # Features: [Placeholder for LSTM output during training, daily_sent]
        # In real training, we'd use the actual LSTM prediction
        fusion_X.append([y_lstm[i], daily_sent]) 
        fusion_y.append(target)
        
    return np.array(fusion_X), np.array(fusion_y)

def train_fusion(X, y):
    model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1)
    model.fit(X, y)
    model.save_model('models/checkpoints/fusion_model.json')
    print("Fusion model trained and saved.")
    return model

if __name__ == "__main__":
    # Logic for training across all stocks would go here
    print("Fusion training script ready.")
