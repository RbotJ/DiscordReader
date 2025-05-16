"""
Market Price Monitor Module

This module provides real-time price monitoring via Alpaca WebSocket feed.
It connects to the Alpaca API, subscribes to tickers, and publishes price
updates to Redis channels.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Set, Callable, Optional

from alpaca.data.live import StockDataStream
from common.redis_utils import get_redis_client

logger = logging.getLogger(__name__)

# Redis event channels
PRICE_UPDATE_CHANNEL = "market.price_update"
TRADE_UPDATE_CHANNEL = "market.trade_update"
TICKER_WATCH_CHANNEL = "market.ticker_watch"
TICKER_UNWATCH_CHANNEL = "market.ticker_unwatch"
CANDLE_UPDATE_CHANNEL = "market.candle_update"
SYSTEM_STATUS_CHANNEL = "system.status"

class PriceMonitor:
    """Real-time price monitor using Alpaca WebSocket API."""
    def __init__(self, api_key=None, api_secret=None):
        """
        Initialize the price monitor.
        
        Args:
            api_key: Alpaca API key (default: from environment)
            api_secret: Alpaca API secret (default: from environment)
        """
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self.api_secret = api_secret or os.environ.get("ALPACA_API_SECRET")
        
        self.watchlist = set()
        self.stock_stream = StockDataStream(self.api_key, self.api_secret)
        self.redis = get_redis_client()
        self.running = False
        
        # Callback registrations
        self.price_callbacks = []
        
    async def start(self):
        """Start the price monitor."""
        self.running = True
        
        # Subscribe to trades for all tickers in watchlist
        if self.watchlist:
            # Convert set to list for subscription
            symbols = list(self.watchlist)
            self.stock_stream.subscribe_trades(self._process_trade, *symbols)
            logger.info(f"Subscribed to trade updates for {len(symbols)} symbols")
        
        try:
            logger.info("Starting Alpaca WebSocket connection...")
            await self.stock_stream.run()
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the price monitor."""
        if self.running:
            self.running = False
            try:
                self.stock_stream.stop()
                logger.info("Stopped Alpaca WebSocket connection")
            except Exception as e:
                logger.error(f"Error stopping WebSocket connection: {e}")
    
    def _process_trade(self, trade):
        """
        Process a trade update from Alpaca.
        
        Args:
            trade: Alpaca trade data
        """
        try:
            symbol = trade.symbol
            price = trade.price
            timestamp = trade.timestamp
            size = trade.size
            
            logger.debug(f"Trade update: {symbol} @ {price} ({timestamp})")
            
            # Create trade event
            event = {
                "symbol": symbol,
                "price": float(price),
                "size": float(size),
                "timestamp": timestamp.isoformat(),
                "event_type": "trade_update"
            }
            
            # Add metadata about this ticker if we have any tracked setups
            # This will be populated by the signal detector system
            event["status"] = "monitoring"  # Default status
            
            # Publish to Redis - both to the general price update channel and to the ticker-specific channel
            if self.redis and self.redis.available:
                # Publish to the general market price update channel
                self.redis.publish(PRICE_UPDATE_CHANNEL, json.dumps(event))
                
                # Also publish to ticker-specific channel for more targeted subscriptions
                self.redis.publish(f"ticker.{symbol}", json.dumps(event))
            
            # Call registered callbacks
            for callback in self.price_callbacks:
                try:
                    callback(symbol, float(price), timestamp)
                except Exception as e:
                    logger.error(f"Error in price callback: {e}")
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
    
    def add_symbols(self, symbols: List[str]):
        """
        Add multiple symbols to the watchlist.
        
        Args:
            symbols: List of ticker symbols to add
        """
        if not symbols:
            return
            
        symbols = [s.upper() for s in symbols]
        new_symbols = []
        
        for symbol in symbols:
            if symbol not in self.watchlist:
                self.watchlist.add(symbol)
                new_symbols.append(symbol)
                
                # Publish individual ticker watch event for each new symbol
                if self.redis and self.redis.available:
                    watch_event = {
                        "symbol": symbol,
                        "event_type": "ticker_watch",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    self.redis.publish(TICKER_WATCH_CHANNEL, json.dumps(watch_event))
                    self.redis.publish(f"ticker.{symbol}.control", json.dumps(watch_event))
        
        if new_symbols:
            # Publish batch ticker watch event
            if self.redis and self.redis.available and len(new_symbols) > 1:
                batch_watch_event = {
                    "symbols": new_symbols,
                    "event_type": "ticker_watch_batch",
                    "count": len(new_symbols),
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.redis.publish(TICKER_WATCH_CHANNEL, json.dumps(batch_watch_event))
            
            if self.running:
                # Resubscribe with updated watchlist
                self.stock_stream.subscribe_trades(self._process_trade, *new_symbols)
                
            logger.info(f"Added {len(new_symbols)} symbols to watchlist: {', '.join(new_symbols)}")
    
    def add_symbol(self, symbol: str):
        """
        Add a symbol to the watchlist.
        
        Args:
            symbol: Ticker symbol to add
        """
        symbol = symbol.upper()
        if symbol not in self.watchlist:
            self.watchlist.add(symbol)
            
            # Publish ticker watch event
            if self.redis and self.redis.available:
                watch_event = {
                    "symbol": symbol,
                    "event_type": "ticker_watch",
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.redis.publish(TICKER_WATCH_CHANNEL, json.dumps(watch_event))
                self.redis.publish(f"ticker.{symbol}.control", json.dumps(watch_event))
                logger.debug(f"Published ticker watch event for {symbol}")
            
            if self.running:
                # Resubscribe for this symbol
                self.stock_stream.subscribe_trades(self._process_trade, symbol)
            logger.info(f"Added {symbol} to watchlist")
    
    def remove_symbol(self, symbol: str):
        """
        Remove a symbol from the watchlist.
        
        Args:
            symbol: Ticker symbol to remove
        """
        symbol = symbol.upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            
            # Publish ticker unwatch event
            if self.redis and self.redis.available:
                unwatch_event = {
                    "symbol": symbol,
                    "event_type": "ticker_unwatch",
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.redis.publish(TICKER_UNWATCH_CHANNEL, json.dumps(unwatch_event))
                self.redis.publish(f"ticker.{symbol}.control", json.dumps(unwatch_event))
                logger.debug(f"Published ticker unwatch event for {symbol}")
            
            if self.running:
                # Unsubscribe from this symbol
                self.stock_stream.unsubscribe_trades(symbol)
            logger.info(f"Removed {symbol} from watchlist")
    
    def register_price_callback(self, callback: Callable[[str, float, datetime], None]):
        """
        Register a callback for price updates.
        
        Args:
            callback: Function to call on price updates (symbol, price, timestamp)
        """
        self.price_callbacks.append(callback)
        logger.debug(f"Registered price callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def get_watchlist(self) -> List[str]:
        """
        Get the current watchlist.
        
        Returns:
            List of ticker symbols being monitored
        """
        return list(self.watchlist)

# Singleton instance
_price_monitor = None

def get_price_monitor() -> PriceMonitor:
    """
    Get the global price monitor instance.
    
    Returns:
        PriceMonitor: Global price monitor instance
    """
    global _price_monitor
    if _price_monitor is None:
        _price_monitor = PriceMonitor()
    return _price_monitor