"""
MarketIntel AI: Neural Sentiment Analyzer
=========================================

Wraps Hugging Face Transformers (DistilBERT) to convert raw financial 
news headlines into normalized sentiment scores (-1.0 to 1.0). Includes 
a rule-based heuristic fallback if the neural pipeline fails to load.
"""
try:
    from transformers import pipeline
    import torch
    HAS_TRANSFORMERS = True
except Exception as e:
    print(f"Warning: Sentiment analysis libraries failed to load: {e}")
    HAS_TRANSFORMERS = False

class SentimentExpert:
    def __init__(self, model_name="distilbert-base-uncased-finetuned-sst-2-english"):
        self.classifier = None
        if HAS_TRANSFORMERS:
            try:
                self.device = 0 if torch.cuda.is_available() else -1
                self.classifier = pipeline("sentiment-analysis", model=model_name, device=self.device)
            except Exception as e:
                print(f"Warning: Sentiment pipeline failed to initialize: {e}")
                
    def get_sentiment(self, text):
        """Returns a sentiment score between -1 (negative) and 1 (positive)."""
        if not text or len(text.strip()) == 0:
            return 0.0
            
        if self.classifier:
            try:
                # DistilBERT max length is 512
                result = self.classifier(text[:512])[0]
                label = result['label']
                score = result['score']
                return score if label == 'POSITIVE' else -score
            except Exception as e:
                print(f"Error in neural sentiment: {e}")
        
        # Simple keyword fallback if neural model is unavailable
        text_lower = text.lower()
        pos_words = ['up', 'gain', 'buy', 'profit', 'surge', 'growth', 'bull', 'positive']
        neg_words = ['down', 'loss', 'sell', 'drop', 'crash', 'bear', 'negative', 'fine']
        
        score = 0
        for w in pos_words: 
            if w in text_lower: score += 0.2
        for w in neg_words: 
            if w in text_lower: score -= 0.2
            
        return max(-1.0, min(1.0, score))


# Singleton instance
_expert = None

def get_sentiment_score(text):
    global _expert
    if _expert is None:
        _expert = SentimentExpert()
    return _expert.get_sentiment(text)
