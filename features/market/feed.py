"""
Real-time Market Data Feed Module

This module provides functionality for subscribing to and consuming real-time
market data, including quotes, trades, and bars/candles.
"""
import os
import logging
import json
import asyncio
import threading
from typing import Dict, List, Set, Optional, Union, Any, Callable
from datetime import datetime
from queue import Queue

from alpaca.data.live import StockDataStream
from alpaca.data.models import QuoteData, TradeData, BarData

from features.market.history import get_latest_price

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

class MarketDataFeed:
    """
    Service for streaming real-time market data.
    """
    
    def __init__(self):
        """Initialize the market data feed."""
        self.stream = None
        self.initialized = False
        self.connected = False
        self.running = False
        self.subscribed_symbols = set()
        self.quote_callbacks = []
        self.trade_callbacks = []
        self.bar_callbacks = []
        
        # Data caches
        self.quotes = {}  # Latest quotes by symbol
        self.trades = {}  # Latest trades by symbol
        self.bars = {}    # Latest bars by symbol
        
        # Initialize client
        self.initialized = self._initialize_stream()
        if self.initialized:
            logger.info("Market data stream initialized successfully")
        else:
            logger.warning("Failed to initialize market data stream")
            
        # Start the feed
        self.start()
        
    def _initialize_stream(self) -> bool:
        """
        Initialize the Alpaca data stream.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not ALPACA_API_KEY or not ALPACA_API_SECRET:
            logger.warning("Alpaca API credentials not found in environment variables")
            return False
            
        try:
            # Create the data stream client
            self.stream = StockDataStream(ALPACA_API_KEY, ALPACA_API_SECRET)
            
            # Set up callbacks
            self.stream.quote_handlers.append(self._handle_quote)
            self.stream.trade_handlers.append(self._handle_trade)
            self.stream.bar_handlers.append(self._handle_bar)
            
            return True
        except Exception as e:
            logger.error(f"Error initializing market data stream: {e}")
            return False
            
    def start(self):
        """Start the market data feed."""
        if not self.initialized or not self.stream:
            logger.warning("Market data stream not initialized")
            return False
            
        if self.running:
            logger.info("Market data feed already running")
            return True
            
        try:
            # Start connection thread
            self.running = True
            self.feed_thread = threading.Thread(target=self._run_feed)
            self.feed_thread.daemon = True
            self.feed_thread.start()
            logger.info("Market data feed started")
            return True
        except Exception as e:
            logger.error(f"Error starting market data feed: {e}")
            self.running = False
            return False
            
    def _run_feed(self):
        """Run the market data feed in a thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect to the stream
            loop.run_until_complete(self._connect())
            
            # Run the event loop
            loop.run_forever()
        except Exception as e:
            logger.error(f"Error in market data feed thread: {e}")
        finally:
            self.running = False
            loop.close()
            
    async def _connect(self):
        """Connect to the data stream."""
        if not self.initialized or not self.stream:
            logger.warning("Market data stream not initialized")
            return
            
        try:
            # Connect to the stream
            await self.stream.connect()
            self.connected = True
            logger.info("Connected to market data stream")
            
            # Resubscribe to any previously subscribed symbols
            if self.subscribed_symbols:
                symbols = list(self.subscribed_symbols)
                await self.stream.subscribe_quotes(symbols)
                await self.stream.subscribe_trades(symbols)
                await self.stream.subscribe_bars(symbols)
                logger.info(f"Resubscribed to {len(symbols)} symbols")
        except Exception as e:
            logger.error(f"Error connecting to market data stream: {e}")
            self.connected = False
            
    def _handle_quote(self, quote: Union[QuoteData, Dict]):
        """
        Handle quote update from the stream.
        
        Args:
            quote: Quote update
        """
        try:
            # Convert to dict if needed
            if not isinstance(quote, dict):
                # Extract symbol
                symbol = quote.symbol
                
                # Format quote data
                quote_dict = {
                    'symbol': symbol,
                    'bid_price': float(quote.bid_price) if quote.bid_price else None,
                    'bid_size': int(quote.bid_size) if quote.bid_size else 0,
                    'ask_price': float(quote.ask_price) if quote.ask_price else None,
                    'ask_size': int(quote.ask_size) if quote.ask_size else 0,
                    'timestamp': quote.timestamp.isoformat() if quote.timestamp else datetime.now().isoformat()
                }
                
                # Calculate mid price
                if quote_dict['bid_price'] and quote_dict['ask_price']:
                    quote_dict['mid_price'] = (quote_dict['bid_price'] + quote_dict['ask_price']) / 2
                else:
                    quote_dict['mid_price'] = None
            else:
                # Already a dict
                symbol = quote.get('symbol')
                quote_dict = quote
                
            # Skip if no symbol
            if not symbol:
                return
                
            # Cache the quote
            self.quotes[symbol] = quote_dict
            
            # Notify callbacks
            for callback in self.quote_callbacks:
                try:
                    callback(quote_dict)
                except Exception as e:
                    logger.error(f"Error in quote callback: {e}")
        except Exception as e:
            logger.error(f"Error handling quote: {e}")
            
    def _handle_trade(self, trade: Union[TradeData, Dict]):
        """
        Handle trade update from the stream.
        
        Args:
            trade: Trade update
        """
        try:
            # Convert to dict if needed
            if not isinstance(trade, dict):
                # Extract symbol
                symbol = trade.symbol
                
                # Format trade data
                trade_dict = {
                    'symbol': symbol,
                    'price': float(trade.price) if trade.price else None,
                    'size': int(trade.size) if trade.size else 0,
                    'timestamp': trade.timestamp.isoformat() if trade.timestamp else datetime.now().isoformat(),
                    'trade_id': trade.id,
                    'exchange': trade.exchange
                }
            else:
                # Already a dict
                symbol = trade.get('symbol')
                trade_dict = trade
                
            # Skip if no symbol
            if not symbol:
                return
                
            # Cache the trade
            self.trades[symbol] = trade_dict
            
            # Notify callbacks
            for callback in self.trade_callbacks:
                try:
                    callback(trade_dict)
                except Exception as e:
                    logger.error(f"Error in trade callback: {e}")
        except Exception as e:
            logger.error(f"Error handling trade: {e}")
            
    def _handle_bar(self, bar: Union[BarData, Dict]):
        """
        Handle bar/candle update from the stream.
        
        Args:
            bar: Bar/candle update
        """
        try:
            # Convert to dict if needed
            if not isinstance(bar, dict):
                # Extract symbol
                symbol = bar.symbol
                
                # Format bar data
                bar_dict = {
                    'symbol': symbol,
                    'open': float(bar.open) if bar.open else None,
                    'high': float(bar.high) if bar.high else None,
                    'low': float(bar.low) if bar.low else None,
                    'close': float(bar.close) if bar.close else None,
                    'volume': int(bar.volume) if bar.volume else 0,
                    'timestamp': bar.timestamp.isoformat() if bar.timestamp else datetime.now().isoformat(),
                    'timeframe': bar.timeframe
                }
            else:
                # Already a dict
                symbol = bar.get('symbol')
                bar_dict = bar
                
            # Skip if no symbol
            if not symbol:
                return
                
            # Cache the bar
            self.bars[symbol] = bar_dict
            
            # Notify callbacks
            for callback in self.bar_callbacks:
                try:
                    callback(bar_dict)
                except Exception as e:
                    logger.error(f"Error in bar callback: {e}")
        except Exception as e:
            logger.error(f"Error handling bar: {e}")
            
    async def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time data for symbols.
        
        Args:
            symbols: List of symbols to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        if not self.initialized or not self.stream:
            logger.warning("Market data stream not initialized")
            return False
            
        if not self.connected:
            logger.warning("Not connected to market data stream")
            return False
            
        try:
            # Add to subscribed symbols
            new_symbols = [s for s in symbols if s not in self.subscribed_symbols]
            for symbol in new_symbols:
                self.subscribed_symbols.add(symbol)
                
            if not new_symbols:
                logger.info("No new symbols to subscribe to")
                return True
                
            # Subscribe to quotes, trades, and bars
            await self.stream.subscribe_quotes(new_symbols)
            await self.stream.subscribe_trades(new_symbols)
            await self.stream.subscribe_bars(new_symbols)
            
            logger.info(f"Subscribed to {len(new_symbols)} symbols")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False
            
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from real-time data for symbols.
        
        Args:
            symbols: List of symbols to unsubscribe from
            
        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        if not self.initialized or not self.stream:
            logger.warning("Market data stream not initialized")
            return False
            
        if not self.connected:
            logger.warning("Not connected to market data stream")
            return False
            
        try:
            # Remove from subscribed symbols
            for symbol in symbols:
                if symbol in self.subscribed_symbols:
                    self.subscribed_symbols.remove(symbol)
                    
            # Unsubscribe from quotes, trades, and bars
            await self.stream.unsubscribe_quotes(symbols)
            await self.stream.unsubscribe_trades(symbols)
            await self.stream.unsubscribe_bars(symbols)
            
            logger.info(f"Unsubscribed from {len(symbols)} symbols")
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing from symbols: {e}")
            return False
            
    def get_last_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get the last quote for a symbol.
        
        Args:
            symbol: Symbol to get quote for
            
        Returns:
            Quote dictionary or None if not available
        """
        return self.quotes.get(symbol)
        
    def get_last_trade(self, symbol: str) -> Optional[Dict]:
        """
        Get the last trade for a symbol.
        
        Args:
            symbol: Symbol to get trade for
            
        Returns:
            Trade dictionary or None if not available
        """
        return self.trades.get(symbol)
        
    def get_last_bar(self, symbol: str) -> Optional[Dict]:
        """
        Get the last bar/candle for a symbol.
        
        Args:
            symbol: Symbol to get bar for
            
        Returns:
            Bar dictionary or None if not available
        """
        return self.bars.get(symbol)
        
    def register_quote_callback(self, callback: Callable[[Dict], None]):
        """
        Register a callback for quote updates.
        
        Args:
            callback: Function to call with quote updates
        """
        self.quote_callbacks.append(callback)
        
    def register_trade_callback(self, callback: Callable[[Dict], None]):
        """
        Register a callback for trade updates.
        
        Args:
            callback: Function to call with trade updates
        """
        self.trade_callbacks.append(callback)
        
    def register_bar_callback(self, callback: Callable[[Dict], None]):
        """
        Register a callback for bar/candle updates.
        
        Args:
            callback: Function to call with bar updates
        """
        self.bar_callbacks.append(callback)
        
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol.
        
        This method tries to get the price from various sources in this order:
        1. Last trade price
        2. Last quote mid price
        3. Last bar close price
        4. Historical data
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Current price or None if not available
        """
        # Try last trade
        trade = self.get_last_trade(symbol)
        if trade and trade.get('price'):
            return trade['price']
            
        # Try last quote
        quote = self.get_last_quote(symbol)
        if quote and quote.get('mid_price'):
            return quote['mid_price']
            
        # Try last bar
        bar = self.get_last_bar(symbol)
        if bar and bar.get('close'):
            return bar['close']
            
        # Try historical data as a last resort
        return get_latest_price(symbol)

# Global instance
_market_feed = MarketDataFeed()

def get_market_feed() -> MarketDataFeed:
    """
    Get the global market data feed instance.
    
    Returns:
        MarketDataFeed instance
    """
    return _market_feed