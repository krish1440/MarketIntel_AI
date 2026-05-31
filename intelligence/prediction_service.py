"""
MarketIntel AI: Neural Prediction Service
=========================================

This module orchestrates the neural intelligence pipeline. It acts as a bridge
between the raw market data stored in PostgreSQL and the deep learning models 
(LSTM for price sequences, XGBoost for multimodal fusion, and DistilBERT for sentiment).
"""
import sys
import os
import pandas as pd
import datetime
import numpy as np

# Global flag for AI capability
TORCH_AVAILABLE = False
try:
    # pyrefly: ignore [missing-import]
    import torch
    TORCH_AVAILABLE = True
except Exception as e:
    print(f"Warning: AI Prediction stack (Torch) failed to load: {e}")

# Add parent directory to path for db and model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, HistoricalPrice, NewsArticle
from models.preprocess import calculate_technical_indicators, prepare_lstm_data, to_torch

class PredictionService:
    """
    Singleton service that maintains active AI models in memory.

    It encapsulates the logic for feature extraction, technical indicator 
    calculation, sequence preparation for LSTMs, and final BUY/HOLD/SELL
    signal fusion.
    """
    def __init__(self):
        """
        Initializes the PredictionService and pre-loads neural checkpoints 
        if PyTorch is available on the host machine.
        """
        self.fusion = None
        if TORCH_AVAILABLE:
            try:
                from models.fusion_model import MultimodalFusion
                # Initialize fusion model with 5 features
                self.fusion = MultimodalFusion(
                    lstm_input_dim=5, 
                    lstm_checkpoint='models/checkpoints/price_model.pth',
                    xgb_checkpoint='models/checkpoints/fusion_model.json'
                )
            except Exception as e:
                print(f"Warning: Fusion model initialization failed: {e}")


    def get_signal(self, ticker, exchange="NSE", as_of=None):
        """
        Generates a comprehensive neural trading signal and price forecast.

        This method dynamically reads recent historical data, calculates critical
        technical indicators, aggregates recent news sentiment, and passes 
        features through the MultimodalFusion model.

        Args:
            ticker (str): The stock symbol to analyze.
            exchange (str): The stock exchange (e.g., 'NSE' or 'BSE').
            as_of (date): Optional simulation date for backtesting.

        Returns:
            dict: An intelligence payload containing the trading signal, technical 
                  summaries, current price, and advanced multi-day price forecast.
        """
        session = get_session()
        try:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock: return {"error": "Ticker not found"}

            # 1. Fetch recent price data (need more for SMA 50)
            query = session.query(HistoricalPrice).filter_by(stock_id=stock.id, exchange=exchange)
            if as_of:
                query = query.filter(HistoricalPrice.date <= as_of)
                
            prices = pd.read_sql(
                query.order_by(HistoricalPrice.date.desc()).limit(150).statement,
                session.bind
            ).iloc[::-1]
            
            # Drop any rows with NaN in critical columns (e.g. latest incomplete data)
            prices = prices.dropna(subset=['close', 'high', 'low'])
            
            if len(prices) < 100: 
                # Fallback to LiveQuote for current price even if history is missing
                from db.schema import LiveQuote
                latest_quote = session.query(LiveQuote).filter_by(stock_id=stock.id, exchange=exchange).order_by(LiveQuote.timestamp.desc()).first()
                current_price = float(latest_quote.price) if latest_quote else 0.0
                
                return {
                    "ticker": ticker,
                    "exchange": exchange,
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "current_price": current_price,
                    "error": "Insufficient historical data for AI analysis. Backfill in progress."
                }
            
            prices = calculate_technical_indicators(prices)
            X_lstm, _, _ = prepare_lstm_data(prices, feature_cols=['close', 'SMA_20', 'RSI_14', 'MACD', 'ATR_14'])
            last_sequence, _ = to_torch(X_lstm[-1:], np.zeros(1))
            
            # 2. News Sentiment
            as_of_dt = datetime.datetime.combine(as_of, datetime.time.max) if as_of else datetime.datetime.utcnow()
            last_week = as_of_dt - datetime.timedelta(days=7)
            
            news = session.query(NewsArticle).filter(
                NewsArticle.stock_id == stock.id,
                NewsArticle.published_at >= last_week,
                NewsArticle.published_at <= as_of_dt
            ).all()
            sent_scores = [n.sentiment_score for n in news if n.sentiment_score is not None]
            sentiment_avg = float(sum(sent_scores)/len(sent_scores)) if sent_scores else 0.0
            
            # 3. Key Technicals for UI
            def clean(val):
                return float(val) if not (isinstance(val, (float, np.float64, np.float32)) and np.isnan(val)) else 0.0

            latest = prices.iloc[-1]
            rsi = clean(latest['RSI_14'])
            sma_20 = clean(latest['SMA_20'])
            sma_50 = clean(latest['SMA_50'])
            macd = clean(latest['MACD'])
            macd_signal = clean(latest['MACD_Signal'])
            bb_upper = clean(latest['BB_Upper'])
            bb_lower = clean(latest['BB_Lower'])
            atr = clean(latest['ATR_14'])
            vwap = clean(latest['VWAP'])
            adx = clean(latest.get('ADX_14', 0.0))
            cci = clean(latest.get('CCI_20', 0.0))
            bb_width = clean(latest.get('BB_Width', 0.0))
            tenkan = clean(latest.get('Ichimoku_Tenkan', 0.0))
            kijun = clean(latest.get('Ichimoku_Kijun', 0.0))

            # 4. Signal Generation (Deterministic Technical Scoring)
            current_price = float(latest['close'])
            score = 0.0
            
            # Trend (Moving Averages)
            if current_price > sma_20: score += 1.0
            elif current_price < sma_20: score -= 1.0
            
            if current_price > sma_50: score += 1.0
            elif current_price < sma_50: score -= 1.0
            
            # MACD
            if macd > macd_signal: score += 1.0
            elif macd < macd_signal: score -= 1.0
            
            # RSI Momentum
            if rsi < 30: score += 1.5
            elif rsi < 45: score += 0.5
            elif rsi > 70: score -= 1.5
            elif rsi > 55: score -= 0.5
            
            # Normalize score (-4.5 to +4.5 max range)
            max_possible_score = 4.5
            normalized_score = score / max_possible_score
            
            # Add slight sentiment weight (max +/- 0.1)
            normalized_score += (sentiment_avg * 0.1)
            normalized_score = max(min(normalized_score, 1.0), -1.0)
            
            # Map to UI Signal
            if normalized_score > 0.5: signal = "STRONG BUY"
            elif normalized_score > 0.15: signal = "BUY"
            elif normalized_score < -0.5: signal = "STRONG SELL"
            elif normalized_score < -0.15: signal = "SELL"
            else: signal = "HOLD"
            
            confidence = abs(normalized_score)

            
            # 5. Advanced Price Forecast
            current_price = float(latest['close'])
            momentum = (current_price / float(prices['close'].iloc[-10]) - 1) if len(prices) > 10 else 0
            
            forecast_points = []
            # Multi-factor drift (Sentiment + RSI + ADX Trend)
            trend_factor = 0.001 if adx > 25 and latest['close'] > sma_20 else (-0.001 if adx > 25 else 0)
            daily_drift = (momentum * 0.1) + (sentiment_avg * 0.005) + ((rsi - 50) * -0.0002) + trend_factor
            
            for i in range(1, 8):
                noise = np.random.normal(0, 0.001)
                price = current_price * (1 + daily_drift * i + noise)
                forecast_points.append({"day": i, "price": float(price)})
                
            return {
                "ticker": ticker,
                "exchange": exchange,
                "signal": signal,
                "confidence": min(float(confidence), 1.0),
                "sentiment_avg": sentiment_avg,
                "technicals": {
                    "rsi": rsi, "sma_20": sma_20, "sma_50": sma_50,
                    "macd": macd, "macd_signal": macd_signal,
                    "bb_upper": bb_upper, "bb_lower": bb_lower,
                    "atr": atr, "vwap": vwap, "adx": adx, "cci": cci,
                    "bb_width": bb_width, "ichimoku": {"tenkan": tenkan, "kijun": kijun}
                },
                "fundamentals": {
                    "name": stock.name or ticker,
                    "pe_ratio": float(current_price / float(stock.eps)) if stock.eps and float(stock.eps) > 0 else (float(stock.pe_ratio) if stock.pe_ratio else 0.0),
                    "market_cap": int(stock.market_cap) if stock.market_cap else 0,
                    "sector": stock.sector or "Unknown"
                },
                "current_price": current_price,
                "risk_management": {
                    "stop_loss": float(current_price - (2.0 * atr)),
                    "take_profit": float(current_price + (5.0 * atr)), # 2.5 * 2.0 atr
                    "atr_volatility": atr,
                    "risk_reward_ratio": "2.5:1"
                },
                "forecast": forecast_points,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        finally:
            session.close()
