"""
MarketIntel AI: Multimodal Fusion Engine
========================================

This module provides the `MultimodalFusion` class which intelligently combines
the sequence predictions from the LSTM with the semantic analysis from the 
Transformers model to generate a unified, high-confidence trading signal.
"""
import xgboost as xgb
import os
import torch
from .price_lstm import PriceLSTM

class MultimodalFusion:
    """
    An orchestrator class that fuses different AI model outputs.

    It loads both the LSTM model (for sequence modeling) and the XGBoost model 
    (for signal classification), generating a final predictive heuristic.
    """
    def __init__(self, lstm_input_dim=5, lstm_checkpoint=None, xgb_checkpoint=None):
        """
        Initializes the fusion engine with appropriate model checkpoints.

        Args:
            lstm_input_dim (int): The number of features expected by the LSTM.
            lstm_checkpoint (str, optional): Path to the PyTorch LSTM weights.
            xgb_checkpoint (str, optional): Path to the XGBoost tree weights.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.lstm_model = PriceLSTM(lstm_input_dim, 64, 2, 1).to(self.device)
        
        if lstm_checkpoint and os.path.exists(lstm_checkpoint):
            print(f"Loading LSTM checkpoint from {lstm_checkpoint}")
            self.lstm_model.load_state_dict(torch.load(lstm_checkpoint, map_location=self.device))
        self.lstm_model.eval()
        
        self.xgb_model = xgb.XGBClassifier()
        if xgb_checkpoint and os.path.exists(xgb_checkpoint):
            self.xgb_model.load_model(xgb_checkpoint)

    def extract_features(self, price_sequence, recent_sentiment_scores):
        """
        Combine LSTM output and sentiment signals into a feature vector.
        """
        # 1. Get LSTM prediction
        with torch.no_grad():
            price_sequence = price_sequence.to(self.device)
            lstm_pred = self.lstm_model(price_sequence).item()
            
        # 2. Process sentiment (mean of recent scores)
        if recent_sentiment_scores:
            sent_avg = sum(recent_sentiment_scores) / len(recent_sentiment_scores)
        else:
            sent_avg = 0.0
            
        # 3. Create feature vector: [lstm_pred, sent_avg]
        return [lstm_pred, sent_avg]

    def predict(self, feature_vector, rsi=50):
        """
        Predicts the final movement signal (1 for BUY, 0 for SELL/HOLD).

        If the XGBoost model is fully trained, it delegates to the XGB Classifier.
        If not, it relies on an advanced multimodal heuristic fallback logic.

        Args:
            feature_vector (list): The combined [lstm_pred, sent_avg] array.
            rsi (float): Current Relative Strength Index value (used in fallback).

        Returns:
            tuple: (Prediction Class (int), Confidence Score (float))
        """
        try:
            if hasattr(self.xgb_model, 'n_features_in_'):
                pred = self.xgb_model.predict([feature_vector])[0]
                probs = self.xgb_model.predict_proba([feature_vector])[0]
                return pred, max(probs)
        except:
            pass
            
        # Advanced Heuristic Fallback (Multimodal Rule-based)
        lstm_score, sent_avg = feature_vector
        
        # LSTM score is the predicted normalized close price.
        # We'll use a threshold-based signal if it's high/low
        
        # BUY Logic
        if rsi < 30 or sent_avg > 0.4 or lstm_score > 0.7:
            return 1, 0.85
        # SELL Logic
        elif rsi > 70 or sent_avg < -0.4 or lstm_score < 0.3:
            return 0, 0.85
        # Trend Following
        elif sent_avg > 0.1 or lstm_score > 0.6:
            return 1, 0.70
        elif sent_avg < -0.1 or lstm_score < 0.4:
            return 0, 0.70
        
        return 0, 0.5 # Default HOLD
