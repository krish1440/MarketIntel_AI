from transformers import pipeline
import torch

class SentimentExpert:
    def __init__(self, model_name="distilbert-base-uncased-finetuned-sst-2-english"):
        # Load the sentiment analysis pipeline
        # This will automatically download the model on the first run
        self.device = 0 if torch.cuda.is_available() else -1
        self.classifier = pipeline("sentiment-analysis", model=model_name, device=self.device)

    def get_sentiment(self, text):
        """
        Returns a sentiment score between -1 (negative) and 1 (positive).
        """
        if not text or len(text.strip()) == 0:
            return 0.0
            
        try:
            # DistilBERT max length is 512
            result = self.classifier(text[:512])[0]
            label = result['label']
            score = result['score']
            
            if label == 'POSITIVE':
                return score
            else:
                return -score
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return 0.0

# Singleton instance
_expert = None

def get_sentiment_score(text):
    global _expert
    if _expert is None:
        _expert = SentimentExpert()
    return _expert.get_sentiment(text)
