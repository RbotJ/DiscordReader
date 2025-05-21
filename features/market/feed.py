"""
Market Data Feed Module

This module provides real-time market data feeds for stocks and options.
"""
import logging
import time
from typing import Dict, List, Optional, Set, Callable
from threading import Lock

from features.alpaca.client import get_stock_data_client, get_latest_bars, get_latest_quotes
from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import MarketDataModel

# Configure logger
logger = logging.getLogger(__name__)

# Global state
_subscribed_tickers = set()
_ticker_data = {}  # Stores latest data for each ticker
_price_callbacks = {}  # Callbacks to be called when price updates
_lock = Lock()  # For thread safety

def subscribe_to_ticker(ticker: str) -> bool:
    """
    Subscribe to real-time data for a ticker.

    Args:
        ticker: Ticker symbol to subscribe to

    Returns:
        Success status
    """
    global _subscribed_tickers

    try:
        with _lock:
            if ticker in _subscribed_tickers:
                logger.info(f"Already subscribed to {ticker}")
                return True

            # Add to subscribed tickers
            _subscribed_tickers.add(ticker)
            logger.info(f"Subscribed to {ticker}")

            # Initialize data
            _ticker_data[ticker] = {
                'latest_price': None,
                'latest_bid': None,
                'latest_ask': None,
                'latest_volume': None,
                'last_updated': time.time()
            }

            # Get initial data
            update_ticker_data(ticker)

            return True
    except Exception as e:
        logger.error(f"Error subscribing to ticker {ticker}: {e}")
        return False

def unsubscribe_from_ticker(ticker: str) -> bool:
    """
    Unsubscribe from a ticker.

    Args:
        ticker: Ticker symbol to unsubscribe from

    Returns:
        Success status
    """
    global _subscribed_tickers

    try:
        with _lock:
            if ticker not in _subscribed_tickers:
                logger.info(f"Not subscribed to {ticker}")
                return True

            # Remove from subscribed tickers
            _subscribed_tickers.remove(ticker)

            # Remove data
            if ticker in _ticker_data:
                del _ticker_data[ticker]

            # Remove callbacks
            if ticker in _price_callbacks:
                del _price_callbacks[ticker]

            logger.info(f"Unsubscribed from {ticker}")
            return True
    except Exception as e:
        logger.error(f"Error unsubscribing from ticker {ticker}: {e}")
        return False

def get_subscribed_tickers() -> Set[str]:
    """
    Get all subscribed tickers.

    Returns:
        Set of subscribed ticker symbols
    """
    return _subscribed_tickers.copy()

def update_ticker_data(ticker: str) -> bool:
    """
    Update data for a ticker.

    Args:
        ticker: Ticker symbol to update

    Returns:
        Success status
    """
    try:
        # Get latest bar
        bars = get_latest_bars([ticker])

        # Get latest quote
        quotes = get_latest_quotes([ticker])

        with _lock:
            if ticker not in _ticker_data:
                _ticker_data[ticker] = {}

            # Update price from bar
            if ticker in bars:
                bar = bars[ticker]
                _ticker_data[ticker]['latest_price'] = bar.get('close')
                _ticker_data[ticker]['latest_volume'] = bar.get('volume')

            # Update bid/ask from quote
            if ticker in quotes:
                quote = quotes[ticker]
                _ticker_data[ticker]['latest_bid'] = quote.get('bid_price')
                _ticker_data[ticker]['latest_ask'] = quote.get('ask_price')

            _ticker_data[ticker]['last_updated'] = time.time()

            # Call price callbacks
            if ticker in _price_callbacks and _ticker_data[ticker].get('latest_price'):
                for callback in _price_callbacks[ticker]:
                    try:
                        callback(ticker, _ticker_data[ticker]['latest_price'])
                    except Exception as e:
                        logger.error(f"Error in price callback for {ticker}: {e}")

            return True
    except Exception as e:
        logger.error(f"Error updating ticker data for {ticker}: {e}")
        return False

def get_latest_price(ticker: str) -> Optional[float]:
    """
    Get latest price for a ticker.

    Args:
        ticker: Ticker symbol

    Returns:
        Latest price or None if not available
    """
    if ticker not in _ticker_data:
        # Subscribe if not already
        subscribe_to_ticker(ticker)

        # Update data
        update_ticker_data(ticker)

    if ticker in _ticker_data:
        # Check if data is stale (older than 60 seconds)
        if _ticker_data[ticker].get('last_updated', 0) < time.time() - 60:
            update_ticker_data(ticker)

        return _ticker_data[ticker].get('latest_price')

    return None

def get_ticker_data(ticker: str) -> Dict:
    """
    Get all data for a ticker.

    Args:
        ticker: Ticker symbol

    Returns:
        Dictionary containing ticker data
    """
    if ticker not in _ticker_data:
        # Subscribe if not already
        subscribe_to_ticker(ticker)

        # Update data
        update_ticker_data(ticker)

    if ticker in _ticker_data:
        return _ticker_data[ticker].copy()

    return {}

def register_price_callback(ticker: str, callback: Callable[[str, float], None]) -> bool:
    """
    Register a callback to be called when price updates.

    Args:
        ticker: Ticker symbol
        callback: Function to call when price updates, takes ticker and price as arguments

    Returns:
        Success status
    """
    global _price_callbacks

    try:
        with _lock:
            if ticker not in _price_callbacks:
                _price_callbacks[ticker] = []

            _price_callbacks[ticker].append(callback)

            # Subscribe if not already
            if ticker not in _subscribed_tickers:
                subscribe_to_ticker(ticker)

            return True
    except Exception as e:
        logger.error(f"Error registering price callback for {ticker}: {e}")
        return False

def initialize_feed() -> bool:
    """
    Initialize the market data feed.

    Returns:
        Success status
    """
    try:
        logger.info("Initializing market data feed...")

        # Check if stock data client is available
        client = get_stock_data_client()
        if not client:
            logger.warning("Stock data client not available")
            return False

        return True
    except Exception as e:
        logger.error(f"Error initializing market data feed: {e}")
        return False