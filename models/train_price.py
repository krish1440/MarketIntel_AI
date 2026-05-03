"""
MarketIntel AI: LSTM Price Model Trainer
========================================

Orchestrates the data extraction, preprocessing, and model training loop
for the core PyTorch LSTM network. Handles both full and incremental training.
"""
import sys
import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
import json
import datetime

# Add parent directory to path for db and model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice
from models.preprocess import calculate_technical_indicators, prepare_lstm_data, to_torch
from models.price_lstm import PriceLSTM

def train_model(incremental=False):
    session = get_session()
    stocks = session.query(Stock).all()
    
    all_X, all_y = [], []
    
    # We'll use this to denormalize for RMSE calculation later
    price_ranges = []

    print(f"{'Incremental' if incremental else 'Full'} training started...")
    for stock in stocks:
        prices = pd.read_sql(
            session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.asc()).statement,
            session.bind
        )
        
        if len(prices) < 100: continue
        
        # In incremental mode, we focus on the most recent data
        if incremental:
            prices = prices.iloc[-200:]
            
        prices = calculate_technical_indicators(prices)
        X, y, scaler = prepare_lstm_data(prices, feature_cols=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14'])
        
        all_X.append(X)
        all_y.append(y)
        price_ranges.append({'min': scaler.data_min_[0], 'max': scaler.data_max_[0]})
    
    if not all_X:
        print("No data found for training.")
        return None

    X = np.concatenate(all_X, axis=0)
    y = np.concatenate(all_y, axis=0)
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.1, random_state=42)
    X_train, y_train = to_torch(X_train, y_train)
    X_val, y_val = to_torch(X_val, y_val)
    
    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=32, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=32, shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PriceLSTM(input_dim=5, hidden_dim=64, num_layers=2).to(device)
    
    # Load existing weights if incremental
    checkpoint_path = 'models/checkpoints/price_model.pth'
    if incremental and os.path.exists(checkpoint_path):
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))
        epochs = 5 # Rapid fine-tuning
    else:
        epochs = 20 # Deep learning
        
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005 if incremental else 0.001)
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(batch_X), batch_y)
            loss.backward()
            optimizer.step()
        
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                val_loss += criterion(model(batch_X), batch_y).item()
        
        avg_val = val_loss / len(val_loader)
        if avg_val < best_val_loss:
            best_val_loss = avg_val
            os.makedirs('models/checkpoints', exist_ok=True)
            torch.save(model.state_dict(), checkpoint_path)

    # Calculate RMSE on validation set (unseen data)
    model.eval()
    with torch.no_grad():
        preds = model(X_val.to(device)).cpu().numpy()
        targets = y_val.cpu().numpy()
        
    mse = np.mean((preds - targets)**2)
    rmse_normalized = np.sqrt(mse)
    
    # Rough estimate of average price error (RMSE * average range)
    avg_range = np.mean([r['max'] - r['min'] for r in price_ranges])
    rmse_currency = float(rmse_normalized * avg_range)

    metadata = {
        "last_train": datetime.datetime.utcnow().isoformat(),
        "rmse_currency": rmse_currency,
        "rmse_normalized": float(rmse_normalized),
        "status": "Healthy",
        "mode": "Incremental" if incremental else "Full"
    }
    
    with open('models/checkpoints/metadata.json', 'w') as f:
        json.dump(metadata, f)
        
    print(f"Training complete. RMSE: ₹{rmse_currency:.2f}")
    session.close()
    return metadata

if __name__ == "__main__":
    train_model()
