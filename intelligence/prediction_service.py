import sys
import os
import pandas as pd
import torch
import datetime
import numpy as np

# Add parent directory to path for db and model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, NewsArticle
from models.preprocess import calculate_technical_indicators, prepare_lstm_data, to_torch
from models.fusion_model import MultimodalFusion

class PredictionService:
    def __init__(self):
        self.session = get_session()
        # Initialize fusion model with 5 features (expanded from 4)
        self.fusion = MultimodalFusion(
            lstm_input_dim=5, 
            lstm_checkpoint='models/checkpoints/price_model.pth',
            xgb_checkpoint='models/checkpoints/fusion_model.json'
        )

    def get_signal(self, ticker, exchange="NSE"):
        stock = self.session.query(Stock).filter_by(ticker=ticker).first()
        if not stock: return {"error": "Ticker not found"}

        # 1. Fetch recent price data (need more for SMA 50)
        prices = pd.read_sql(
            self.session.query(HistoricalPrice).filter_by(stock_id=stock.id, exchange=exchange).order_by(HistoricalPrice.date.desc()).limit(150).statement,
            self.session.bind
        ).iloc[::-1]
        
        if len(prices) < 100: 
            return {
                "ticker": ticker,
                "exchange": exchange,
                "signal": "HOLD",
                "confidence": 0.0,
                "error": "Insufficient historical data for high-fidelity indicators"
            }
        
        prices = calculate_technical_indicators(prices)
        X_lstm, _, _ = prepare_lstm_data(prices, feature_cols=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14'])
        last_sequence, _ = to_torch(X_lstm[-1:], np.zeros(1))
        
        # 2. News Sentiment
        last_week = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        news = self.session.query(NewsArticle).filter(
            NewsArticle.stock_id == stock.id,
            NewsArticle.published_at >= last_week
        ).all()
        sent_scores = [n.sentiment_score for n in news if n.sentiment_score is not None]
        sentiment_avg = float(sum(sent_scores)/len(sent_scores)) if sent_scores else 0.0
        
        # 3. Key Technicals for UI
        latest = prices.iloc[-1]
        rsi = float(latest['RSI_14'])
        sma_20 = float(latest['SMA_20'])
        sma_50 = float(latest['SMA_50'])
        macd = float(latest['MACD'])
        macd_signal = float(latest['MACD_Signal'])
        bb_upper = float(latest['BB_Upper'])
        bb_lower = float(latest['BB_Lower'])
        atr = float(latest['ATR_14'])
        vwap = float(latest['VWAP'])

        # 4. Fusion Prediction
        features = self.fusion.extract_features(last_sequence, sent_scores)
        pred, confidence = self.fusion.predict(features, rsi=rsi)
        
        signal = "BUY" if pred == 1 else "SELL"
        if confidence < 0.6: signal = "HOLD"
        
        # 5. Advanced Price Forecast
        current_price = float(latest['close'])
        momentum = (current_price / float(prices['close'].iloc[-10]) - 1) if len(prices) > 10 else 0
        
        forecast_points = []
        # Multi-factor drift
        daily_drift = (momentum * 0.1) + (sentiment_avg * 0.005) + ((rsi - 50) * -0.0002)
        
        for i in range(1, 8):
            noise = np.random.normal(0, 0.001)
            price = current_price * (1 + daily_drift * i + noise)
            forecast_points.append({"day": i, "price": float(price)})
            
        return {
            "ticker": ticker,
            "exchange": exchange,
            "signal": signal,
            "confidence": float(confidence),
            "sentiment_avg": sentiment_avg,
            "technicals": {
                "rsi": rsi,
                "sma_20": sma_20,
                "sma_50": sma_50,
                "macd": macd,
                "macd_signal": macd_signal,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "atr": atr,
                "vwap": vwap
            },
            "current_price": current_price,
            "forecast": forecast_points,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
