import sys
import os

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, NewsArticle
from models.sentiment_model import get_sentiment_score

def update_sentiment():
    session = get_session()
    
    # Fetch articles without sentiment scores
    articles = session.query(NewsArticle).filter(NewsArticle.sentiment_score == None).all()
    
    if not articles:
        print("No new articles to process.")
        return

    print(f"Processing sentiment for {len(articles)} articles...")
    
    count = 0
    for article in articles:
        # Combine title and summary for better context
        text = f"{article.title}. {article.summary if article.summary else ''}"
        score = get_sentiment_score(text)
        
        article.sentiment_score = score
        count += 1
        
        if count % 10 == 0:
            print(f"  Processed {count} articles...")
            session.commit()
            
    session.commit()
    print(f"Finished. Updated {count} articles.")
    session.close()

if __name__ == "__main__":
    update_sentiment()
