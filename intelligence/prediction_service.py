import sys
import os
import pandas as pd
import torch
import datetime

# Add parent directory to path for db and model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, NewsArticle
from models.preprocess import calculate_technical_indicators, prepare_lstm_data, to_torch
from models.fusion_model import MultimodalFusion

class PredictionService:
    def __init__(self):
        self.session = get_session()
        # Initialize fusion model with 4 features (as defined in preprocess.py: feature_cols)
        # Assuming input_dim=4 for LSTM
        self.fusion = MultimodalFusion(
            lstm_input_dim=4,
            lstm_checkpoint='models/checkpoints/price_model.pth',
            xgb_checkpoint='models/checkpoints/fusion_model.json'
        )

    def get_signal(self, ticker):
        stock = self.session.query(Stock).filter_by(ticker=ticker).first()
        if not stock: return {"error": "Ticker not found"}

        # 1. Fetch recent price data (need last 60 days + indicators)
        prices = pd.read_sql(
            self.session.query(HistoricalPrice).filter_by(stock_id=stock.id).order_by(HistoricalPrice.date.desc()).limit(100).statement,
            self.session.bind
        ).iloc[::-1] # Reverse to chronological
        
        if len(prices) < 70: return {"error": "Insufficient historical data"}
        
        prices = calculate_technical_indicators(prices)
        X_lstm, _, _ = prepare_lstm_data(prices)
        last_sequence, _ = to_torch(X_lstm[-1:], np.zeros(1))
        
        # 2. Fetch recent news sentiment (last 24h)
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        news = self.session.query(NewsArticle).filter(
            NewsArticle.stock_id == stock.id,
            NewsArticle.published_at >= yesterday
        ).all()
        
        sent_scores = [n.sentiment_score for n in news if n.sentiment_score is not None]
        
        # 3. Fusion Prediction
        features = self.fusion.extract_features(last_sequence, sent_scores)
        pred, confidence = self.fusion.predict(features)
        
        signal = "BUY" if pred == 1 else "SELL"
        if confidence < 0.6: signal = "HOLD"
        
        return {
            "ticker": ticker,
            "exchange": stock.exchange,
            "signal": signal,
            "confidence": float(confidence),
            "sentiment_avg": float(sum(sent_scores)/len(sent_scores)) if sent_scores else 0.0,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    service = PredictionService()
    # Simple test logic here
    print("Prediction service initialized.")
