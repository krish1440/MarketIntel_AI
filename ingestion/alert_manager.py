"""
MARKETINTEL AI: ALERT DISPATCHER & MANAGER
==========================================

This module centralizes the logic for detecting and dispatching market alerts.
It acts as a bridge between the ingestion streams (Price/News) and the 
persistence layer for notifications.

Key Features:
- Threshold Validation (Price & Sentiment).
- Anti-Spam Logic (Prevents redundant alerts within a cooldown period).
- Centralized Alert Persistence.

Maintainer: MarketIntel AI Intelligence Team
Version: 1.0.0
"""

import datetime
from sqlalchemy import desc
from db.schema import get_session, Alert, Watchlist, Stock

class AlertManager:
    """Manages the detection and recording of market alerts."""

    def __init__(self, session=None):
        """Initializes the manager with a database session."""
        self.session = session if session else get_session()
        self.cooldown_minutes = 60 # Prevent duplicate alerts for 1 hour

    def _is_on_cooldown(self, stock_id, alert_type):
        """Checks if an alert of the same type was recently sent for a stock."""
        last_alert = self.session.query(Alert).filter_by(
            stock_id=stock_id, 
            alert_type=alert_type
        ).order_by(desc(Alert.timestamp)).first()

        if not last_alert:
            return False

        time_diff = datetime.datetime.utcnow() - last_alert.timestamp
        return time_diff.total_seconds() < (self.cooldown_minutes * 60)

    def trigger_alert(self, stock_id, alert_type, message, trigger_value):
        """Persists a new alert to the database if not on cooldown.
        
        Args:
            stock_id: ID of the stock.
            alert_type: String identifier (e.g., 'PRICE_ABOVE').
            message: The human-readable alert message.
            trigger_value: The value that triggered the alert.
        """
        if self._is_on_cooldown(stock_id, alert_type):
            return False

        alert = Alert(
            stock_id=stock_id,
            alert_type=alert_type,
            message=message,
            trigger_value=trigger_value
        )
        self.session.add(alert)
        self.session.commit()
        print(f"🔔 ALERT TRIGGERED: {message}")
        return True

    def check_price_alerts(self, stock_id, current_price, ticker):
        """Checks if the current price violates any watchlist thresholds.
        
        Args:
            stock_id: ID of the stock.
            current_price: The latest market price.
            ticker: The stock ticker for the message.
        """
        watchlist = self.session.query(Watchlist).filter_by(
            stock_id=stock_id, 
            is_active=1
        ).first()

        if not watchlist:
            return

        # Check Price Above
        if watchlist.target_price_above and current_price >= watchlist.target_price_above:
            msg = f"🚀 {ticker} Breakout! Price ₹{current_price:.2f} is above target ₹{watchlist.target_price_above:.2f}"
            self.trigger_alert(stock_id, 'PRICE_ABOVE', msg, current_price)

        # Check Price Below
        if watchlist.target_price_below and current_price <= watchlist.target_price_below:
            msg = f"📉 {ticker} Breakdown! Price ₹{current_price:.2f} is below support ₹{watchlist.target_price_below:.2f}"
            self.trigger_alert(stock_id, 'PRICE_BELOW', msg, current_price)

    def check_sentiment_alerts(self, stock_id, sentiment_score, ticker):
        """Checks if a new sentiment score violates watchlist thresholds.
        
        Args:
            stock_id: ID of the stock.
            sentiment_score: The AI-generated sentiment score.
            ticker: The stock ticker for the message.
        """
        watchlist = self.session.query(Watchlist).filter_by(
            stock_id=stock_id, 
            is_active=1
        ).first()

        if not watchlist or not watchlist.sentiment_threshold:
            return

        if abs(sentiment_score) >= watchlist.sentiment_threshold:
            sentiment_type = "BULLISH" if sentiment_score > 0 else "BEARISH"
            msg = f"🧠 {ticker} Neural Sentiment Spike! {sentiment_type} score of {sentiment_score:.4f} detected."
            self.trigger_alert(stock_id, 'SENTIMENT_SPIKE', msg, sentiment_score)

    def close(self):
        """Closes the database session."""
        if self.session:
            self.session.close()
