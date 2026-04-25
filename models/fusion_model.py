import xgboost as xgb
import os
import torch
from .price_model import StockLSTM
from .sentiment_model import get_sentiment_score

class MultimodalFusion:
    def __init__(self, lstm_input_dim, lstm_checkpoint=None, xgb_checkpoint=None):
        self.lstm_model = StockLSTM(lstm_input_dim, 64, 2, 1)
        if lstm_checkpoint and os.path.exists(lstm_checkpoint):
            self.lstm_model.load_state_dict(torch.load(lstm_checkpoint))
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
            lstm_pred = self.lstm_model(price_sequence).item()
            
        # 2. Process sentiment (mean of recent scores)
        if recent_sentiment_scores:
            sent_avg = sum(recent_sentiment_scores) / len(recent_sentiment_scores)
        else:
            sent_avg = 0.0
            
        # 3. Create feature vector: [lstm_pred, sentiment_avg]
        return [lstm_pred, sent_avg]

    def predict(self, feature_vector):
        """
        Predict final movement using XGBoost.
        """
        # XGBoost expects 2D array
        pred = self.xgb_model.predict([feature_vector])[0]
        probs = self.xgb_model.predict_proba([feature_vector])[0]
        return pred, max(probs)
