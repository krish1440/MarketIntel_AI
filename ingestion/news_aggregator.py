import feedparser
import datetime
import sys
import os
import time
import random
from bs4 import BeautifulSoup
import urllib.parse

# Add parent directory to path for db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import get_session, Stock, NewsArticle

# Global cache of URLs to avoid DB lookups
processed_urls = set()

def load_url_cache(session):
    global processed_urls
    print("Loading news URL cache...", flush=True)
    urls = session.query(NewsArticle.url).all()
    processed_urls = {u[0] for u in urls}
    print(f"Cache loaded with {len(processed_urls)} articles.", flush=True)

def save_article(session, stock_id, entry):
    if entry.link in processed_urls:
        return False
        
    summary_text = ""
    if hasattr(entry, 'summary'):
        soup = BeautifulSoup(entry.summary, 'html.parser')
        summary_text = soup.get_text()
    
    pub_date = datetime.datetime.now()
    if hasattr(entry, 'published'):
        try:
            pub_date = datetime.datetime(*entry.published_parsed[:6])
        except: pass
        
    article = NewsArticle(
        stock_id=stock_id,
        title=entry.title,
        summary=summary_text[:500],
        url=entry.link,
        published_at=pub_date,
        sentiment_score=0.0 # To be updated by sentiment engine
    )
    session.add(article)
    processed_urls.add(entry.link)
    return True

def fetch_broad_market_news(session, stocks):
    """Fetches general Indian market news and maps headlines to specific stocks"""
    print("Fetching broad market headlines...", flush=True)
    rss_urls = [
        "https://news.google.com/rss/search?q=NSE+BSE+Stock+Market+India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Nifty+50+Sensex+Business+News&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    
    new_count = 0
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Logic: If headline mentions a stock ticker or name, link it
                for stock in stocks:
                    if stock.ticker in entry.title or stock.name.split(' ')[0] in entry.title:
                        if save_article(session, stock.id, entry):
                            new_count += 1
        except Exception as e:
            print(f"  Error in broad fetch: {e}", flush=True)
            
    session.commit()
    print(f"  Mapped {new_count} broad articles to specific stocks.", flush=True)

def fetch_specific_news(session, stock):
    """Fetches targeted news for a specific stock ticker"""
    query = f"{stock.ticker} share price news"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(rss_url)
        count = 0
        for entry in feed.entries[:5]: # Take top 5 latest
            if save_article(session, stock.id, entry):
                count += 1
        session.commit()
        if count > 0:
            print(f"  Saved {count} new articles for {stock.ticker}", flush=True)
    except Exception as e:
        print(f"  Error for {stock.ticker}: {e}", flush=True)
        session.rollback()

def main():
    session = get_session()
    load_url_cache(session)
    
    stocks = session.query(Stock).all()
    if not stocks:
        print("No stocks found.", flush=True)
        return

    print(f"News Engine Started for {len(stocks)} stocks.", flush=True)
    
    while True:
        # 1. Broad Discovery (Every loop)
        fetch_broad_market_news(session, stocks)
        
        # 2. Shuffled Specific Discovery
        shuffled_stocks = list(stocks)
        random.shuffle(shuffled_stocks)
        
        for stock in shuffled_stocks:
            # Check if we already have fresh news (skip if news exists from last 12h)
            last_article = session.query(NewsArticle).filter_by(stock_id=stock.id).order_by(NewsArticle.published_at.desc()).first()
            if last_article and (datetime.datetime.now() - last_article.published_at).total_seconds() < 43200:
                continue
                
            fetch_specific_news(session, stock)
            
            # Anti-Ban Protection
            time.sleep(random.uniform(2, 5))
            
        print("🔄 Full cycle complete. Resting for 10 minutes...", flush=True)
        time.sleep(600)

if __name__ == "__main__":
    main()
