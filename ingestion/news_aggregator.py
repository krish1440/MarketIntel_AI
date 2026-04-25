import feedparser
import datetime
import sys
import os
from bs4 import BeautifulSoup
import urllib.parse

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, NewsArticle

def fetch_news_for_stock(session, stock):
    # Google News RSS for the stock ticker
    query = f"{stock.ticker} share price NSE BSE"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    print(f"Fetching news for {stock.ticker}...")
    
    try:
        feed = feedparser.parse(rss_url)
        count = 0
        
        for entry in feed.entries:
            # Check if article already exists
            existing = session.query(NewsArticle).filter_by(url=entry.link).first()
            
            if not existing:
                # Clean summary (often contains HTML in Google News RSS)
                summary_text = ""
                if hasattr(entry, 'summary'):
                    soup = BeautifulSoup(entry.summary, 'html.parser')
                    summary_text = soup.get_text()
                
                # Parse date
                pub_date = datetime.datetime.now()
                if hasattr(entry, 'published'):
                    try:
                        # feedparser handles common date formats
                        pub_date = datetime.datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                article = NewsArticle(
                    stock_id=stock.id,
                    title=entry.title,
                    summary=summary_text[:500], # Cap summary length
                    url=entry.link,
                    published_at=pub_date
                )
                session.add(article)
                count += 1
        
        session.commit()
        print(f"  Saved {count} new articles.")
        
    except Exception as e:
        print(f"  Error fetching news for {stock.ticker}: {e}")
        session.rollback()

def main():
    session = get_session()
    stocks = session.query(Stock).all()
    
    if not stocks:
        print("No stocks found in database.")
        return

    for stock in stocks:
        fetch_news_for_stock(session, stock)
    
    session.close()
    print("News aggregation complete.")

if __name__ == "__main__":
    main()
