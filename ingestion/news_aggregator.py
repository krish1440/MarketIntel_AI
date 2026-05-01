"""
MARKETINTEL AI: REAL-TIME NEWS AGGREGATOR
=========================================

This module implements a sophisticated news scraping and analysis engine. 
It monitors global financial news via RSS, maps headlines to specific stock 
assets, and performs real-time AI sentiment analysis using DistilBERT.

Key Features:
- Dual-Mode Fetching (Broad Market vs. Ticker-Specific).
- Real-Time AI Sentiment Analysis (-1.0 to 1.0).
- Anti-Ban Protection (Randomized Jitter & Rotational Fetching).
- URL Idempotency Cache to minimize database overhead.

Maintainer: MarketIntel AI Intelligence Team
Version: 1.1.0
"""

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
from models.sentiment_model import get_sentiment_score

# Global cache of URLs to avoid redundant DB lookups in high-frequency loops
processed_urls = set()

def load_url_cache(session):
    """Populates the in-memory URL cache from the database.
    
    Args:
        session: The SQLAlchemy database session.
    """
    global processed_urls
    print("Loading news URL cache...", flush=True)
    urls = session.query(NewsArticle.url).all()
    processed_urls = {u[0] for u in urls}
    print(f"Cache loaded with {len(processed_urls)} articles.", flush=True)

def save_article(session, stock_id, entry):
    """Processes and persists a single news article entry.
    
    Args:
        session: The SQLAlchemy database session.
        stock_id: The ID of the related stock.
        entry: The feedparser entry object.
        
    Returns:
        Boolean indicating if the article was newly saved.
    """
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
        
    # Calculate AI Sentiment Score in real-time
    text_to_analyze = f"{entry.title}. {summary_text[:200]}"
    try:
        score = get_sentiment_score(text_to_analyze)
    except:
        score = 0.0

    article = NewsArticle(
        stock_id=stock_id,
        title=entry.title,
        summary=summary_text[:500],
        url=entry.link,
        published_at=pub_date,
        sentiment_score=score
    )
    session.add(article)
    processed_urls.add(entry.link)
    return True

def fetch_broad_market_news(session, stocks):
    """Fetches general Indian market news and maps headlines to specific stocks.
    
    Args:
        session: The SQLAlchemy database session.
        stocks: List of Stock ORM objects to scan for.
    """
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
                # Mapping Logic: If headline mentions a ticker or name, link it
                for stock in stocks:
                    if stock.ticker in entry.title or stock.name.split(' ')[0] in entry.title:
                        if save_article(session, stock.id, entry):
                            new_count += 1
        except Exception as e:
            print(f"  Error in broad fetch: {e}", flush=True)
            
    session.commit()
    print(f"  Mapped {new_count} broad articles to specific stocks.", flush=True)

def fetch_specific_news(session, stock):
    """Fetches targeted news for a specific stock ticker.
    
    Args:
        session: The SQLAlchemy database session.
        stock: The Stock ORM object.
    """
    query = f"{stock.ticker} share price news"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(rss_url)
        count = 0
        for entry in feed.entries[:5]: # Take top 5 latest results
            if save_article(session, stock.id, entry):
                count += 1
        session.commit()
        if count > 0:
            print(f"  Saved {count} new articles for {stock.ticker}", flush=True)
    except Exception as e:
        print(f"  Error for {stock.ticker}: {e}", flush=True)
        session.rollback()

def main():
    """Main loop for the News Aggregation engine."""
    session = get_session()
    load_url_cache(session)
    
    stocks = session.query(Stock).all()
    if not stocks:
        print("No stocks found.", flush=True)
        return

    print(f"News Engine Started for {len(stocks)} stocks.", flush=True)
    
    while True:
        # 1. Broad Discovery (Runs every loop for overall market mood)
        fetch_broad_market_news(session, stocks)
        
        # 2. Shuffled Specific Discovery (Deep dive into individual tickers)
        shuffled_stocks = list(stocks)
        random.shuffle(shuffled_stocks)
        
        for stock in shuffled_stocks:
            # Check if we already have fresh news (skip if news exists from last 12h)
            last_article = session.query(NewsArticle).filter_by(stock_id=stock.id).order_by(NewsArticle.published_at.desc()).first()
            if last_article and (datetime.datetime.now() - last_article.published_at).total_seconds() < 43200:
                continue
                
            fetch_specific_news(session, stock)
            
            # Anti-Ban Protection: Randomized delay
            time.sleep(random.uniform(2, 5))
            
        print("🔄 Full cycle complete. Resting for 10 minutes...", flush=True)
        time.sleep(600)

if __name__ == "__main__":
    main()

