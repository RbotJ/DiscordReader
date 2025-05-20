"""
Real-time Market Data Feed

This module provides real-time stock and options market data using Alpaca's
streaming API. It manages connections, subscriptions, and data distribution.
"""
import os
import logging
import asyncio
import json
from typing import Dict, List, Set, Callable, Optional, Any
from datetime import datetime

from alpaca.data.live import StockDataStream
from alpaca.common.exceptions import APIError

from common.redis_utils import get_redis_client

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

class MarketDataFeed:
    """
    Real-time market data feed using Alpaca's streaming API.
    
    This class manages subscriptions to real-time market data and
    distributes updates to interested components via callbacks and Redis.
    """
    
    def __init__(self):
        self.client = None
        self.redis = get_redis_client()
        self.running = False
        self.connected = False
        self.subscribed_symbols: Set[str] = set()
        self.callbacks: Dict[str, List[Callable]] = {
            'trade': [],
            'quote': [],
            'bar': [],
            'status': []
        }
        self.last_trade: Dict[str, Dict] = {}
        self.last_quote: Dict[str, Dict] = {}
        
    async def connect(self) -> bool:
        """
        Connect to Alpaca's streaming API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not ALPACA_API_KEY or not ALPACA_API_SECRET:
            logger.warning("Alpaca API credentials not found in environment variables")
            return False
            
        try:
            self.client = StockDataStream(ALPACA_API_KEY, ALPACA_API_SECRET)
            
            # Set up handlers
            self.client.subscribe_trades(self._handle_trade, *self.subscribed_symbols)
            self.client.subscribe_quotes(self._handle_quote, *self.subscribed_symbols)
            self.client.subscribe_bars(self._handle_bar, *self.subscribed_symbols)
            
            # Connect
            await self.client.connect()
            self.connected = True
            logger.info("Connected to Alpaca streaming API")
            
            # Notify status callbacks
            for callback in self.callbacks['status']:
                try:
                    callback({'status': 'connected'})
                except Exception as e:
                    logger.error(f"Error in status callback: {e}")
                    
            return True
        except Exception as e:
            logger.error(f"Error connecting to Alpaca streaming API: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from Alpaca's streaming API."""
        if self.client and self.connected:
            try:
                await self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from Alpaca streaming API")
                
                # Notify status callbacks
                for callback in self.callbacks['status']:
                    try:
                        callback({'status': 'disconnected'})
                    except Exception as e:
                        logger.error(f"Error in status callback: {e}")
            except Exception as e:
                logger.error(f"Error disconnecting from Alpaca streaming API: {e}")
                
    async def subscribe(self, symbols: List[str]):
        """
        Subscribe to real-time data for the given symbols.
        
        Args:
            symbols: List of ticker symbols to subscribe to
        """
        if not symbols:
            return
            
        # Track new symbols
        new_symbols = [sym for sym in symbols if sym not in self.subscribed_symbols]
        if not new_symbols:
            return
            
        for symbol in new_symbols:
            self.subscribed_symbols.add(symbol)
            
        # If connected, update subscriptions
        if self.client and self.connected:
            try:
                await self.client.subscribe_trades(self._handle_trade, *new_symbols)
                await self.client.subscribe_quotes(self._handle_quote, *new_symbols)
                await self.client.subscribe_bars(self._handle_bar, *new_symbols)
                logger.info(f"Subscribed to {len(new_symbols)} new symbols")
            except Exception as e:
                logger.error(f"Error subscribing to symbols: {e}")
                
    async def unsubscribe(self, symbols: List[str]):
        """
        Unsubscribe from real-time data for the given symbols.
        
        Args:
            symbols: List of ticker symbols to unsubscribe from
        """
        if not symbols:
            return
            
        # Track symbols to remove
        to_remove = [sym for sym in symbols if sym in self.subscribed_symbols]
        if not to_remove:
            return
            
        for symbol in to_remove:
            self.subscribed_symbols.remove(symbol)
            
        # If connected, update subscriptions
        if self.client and self.connected:
            try:
                await self.client.unsubscribe_trades(*to_remove)
                await self.client.unsubscribe_quotes(*to_remove)
                await self.client.unsubscribe_bars(*to_remove)
                logger.info(f"Unsubscribed from {len(to_remove)} symbols")
            except Exception as e:
                logger.error(f"Error unsubscribing from symbols: {e}")
                
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: Event type ('trade', 'quote', 'bar', 'status')
            callback: Callback function to be called with event data
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            
    def unregister_callback(self, event_type: str, callback: Callable):
        """
        Unregister a callback for a specific event type.
        
        Args:
            event_type: Event type ('trade', 'quote', 'bar', 'status')
            callback: Callback function to remove
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            
    async def start(self):
        """Start the market data feed."""
        if self.running:
            return
            
        self.running = True
        await self.connect()
        logger.info("Market data feed started")
        
    async def stop(self):
        """Stop the market data feed."""
        if not self.running:
            return
            
        self.running = False
        await self.disconnect()
        logger.info("Market data feed stopped")
        
    def get_last_trade(self, symbol: str) -> Optional[Dict]:
        """
        Get the last trade for a symbol.
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Last trade data or None if not available
        """
        return self.last_trade.get(symbol)
        
    def get_last_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get the last quote for a symbol.
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Last quote data or None if not available
        """
        return self.last_quote.get(symbol)
        
    def _handle_trade(self, data: Dict):
        """
        Handle trade data from Alpaca.
        
        Args:
            data: Trade data
        """
        try:
            symbol = data.get('symbol')
            if not symbol:
                return
                
            # Store last trade
            self.last_trade[symbol] = data
            
            # Publish to Redis
            if self.redis:
                try:
                    channel = f"market:trade:{symbol}"
                    self.redis.publish(channel, json.dumps(data))
                except Exception as e:
                    logger.warning(f"Error publishing trade to Redis: {e}")
                    
            # Notify callbacks
            for callback in self.callbacks['trade']:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in trade callback: {e}")
        except Exception as e:
            logger.error(f"Error handling trade: {e}")
            
    def _handle_quote(self, data: Dict):
        """
        Handle quote data from Alpaca.
        
        Args:
            data: Quote data
        """
        try:
            symbol = data.get('symbol')
            if not symbol:
                return
                
            # Store last quote
            self.last_quote[symbol] = data
            
            # Publish to Redis
            if self.redis:
                try:
                    channel = f"market:quote:{symbol}"
                    self.redis.publish(channel, json.dumps(data))
                except Exception as e:
                    logger.warning(f"Error publishing quote to Redis: {e}")
                    
            # Notify callbacks
            for callback in self.callbacks['quote']:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in quote callback: {e}")
        except Exception as e:
            logger.error(f"Error handling quote: {e}")
            
    def _handle_bar(self, data: Dict):
        """
        Handle bar data from Alpaca.
        
        Args:
            data: Bar data
        """
        try:
            symbol = data.get('symbol')
            if not symbol:
                return
                
            # Publish to Redis
            if self.redis:
                try:
                    channel = f"market:bar:{symbol}"
                    self.redis.publish(channel, json.dumps(data))
                except Exception as e:
                    logger.warning(f"Error publishing bar to Redis: {e}")
                    
            # Notify callbacks
            for callback in self.callbacks['bar']:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in bar callback: {e}")
        except Exception as e:
            logger.error(f"Error handling bar: {e}")

# Global instance
market_feed = MarketDataFeed()

async def initialize():
    """Initialize the market data feed."""
    await market_feed.start()
    
def get_market_feed() -> MarketDataFeed:
    """
    Get the global market data feed instance.
    
    Returns:
        MarketDataFeed instance
    """
    return market_feed