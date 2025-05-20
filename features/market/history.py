"""
Historical Market Data Module

This module provides functionality for retrieving historical market data,
including bars/candles for various timeframes and symbol information.
"""
import os
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

class HistoricalDataProvider:
    """
    Service for retrieving historical market data.
    """
    
    def __init__(self):
        """Initialize the historical data provider."""
        self.client = None
        self.initialized = False
        self.cache = {}  # Simple cache for historical data
        self.cache_ttl = 60  # Cache TTL in seconds
        self.initialized = self._initialize_client()
        
        if self.initialized:
            logger.info("Historical data client initialized successfully")
        else:
            logger.warning("Failed to initialize historical data client")
            
    def _initialize_client(self) -> bool:
        """
        Initialize the Alpaca historical data client.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not ALPACA_API_KEY or not ALPACA_API_SECRET:
            logger.warning("Alpaca API credentials not found in environment variables")
            return False
            
        try:
            self.client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
            return True
        except Exception as e:
            logger.error(f"Error initializing historical data client: {e}")
            return False
            
    def _parse_timeframe(self, timeframe_str: str) -> TimeFrame:
        """
        Parse a timeframe string into a TimeFrame object.
        
        Args:
            timeframe_str: Timeframe string (e.g., '1m', '5m', '1h', '1d')
            
        Returns:
            TimeFrame object
        """
        # Parse the number and unit
        if timeframe_str.endswith('m'):
            multiplier = int(timeframe_str[:-1])
            return TimeFrame.Minute(multiplier)
        elif timeframe_str.endswith('h'):
            multiplier = int(timeframe_str[:-1])
            return TimeFrame.Hour(multiplier)
        elif timeframe_str.endswith('d'):
            multiplier = int(timeframe_str[:-1])
            return TimeFrame.Day(multiplier)
        else:
            # Default to 1 minute
            logger.warning(f"Unknown timeframe: {timeframe_str}, using 1m")
            return TimeFrame.Minute(1)
            
    def _format_candle(self, symbol: str, bar: Any) -> Dict:
        """
        Format a bar/candle object into a dictionary.
        
        Args:
            symbol: Symbol for the bar/candle
            bar: Bar/candle object from Alpaca
            
        Returns:
            Formatted candle dictionary
        """
        return {
            'symbol': symbol,
            'timestamp': bar.timestamp.isoformat(),
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': int(bar.volume)
        }
        
    def get_candles(
        self,
        symbol: str,
        timeframe: str = '5m',
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get historical candle data for a symbol.
        
        Args:
            symbol: Symbol to get data for
            timeframe: Candle timeframe (e.g., '1m', '5m', '1h', '1d')
            start: Start date/time (optional)
            end: End date/time (optional)
            limit: Maximum number of candles to return
            
        Returns:
            List of candle dictionaries
        """
        if not self.initialized or not self.client:
            logger.warning("Historical data client not initialized")
            return []
            
        try:
            # Parse timeframe
            tf = self._parse_timeframe(timeframe)
            
            # Set default start/end times if not provided
            if end is None:
                end = datetime.now(timezone.utc)
            elif isinstance(end, str):
                end = datetime.fromisoformat(end.replace('Z', '+00:00'))
                
            if start is None:
                # Calculate start time based on timeframe and limit
                if timeframe.endswith('m'):
                    multiplier = int(timeframe[:-1])
                    start = end - timedelta(minutes=multiplier * limit)
                elif timeframe.endswith('h'):
                    multiplier = int(timeframe[:-1])
                    start = end - timedelta(hours=multiplier * limit)
                elif timeframe.endswith('d'):
                    multiplier = int(timeframe[:-1])
                    start = end - timedelta(days=multiplier * limit)
                else:
                    start = end - timedelta(minutes=limit)
            elif isinstance(start, str):
                start = datetime.fromisoformat(start.replace('Z', '+00:00'))
                
            # Create request
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                limit=limit,
                adjustment=Adjustment.ALL
            )
            
            # Get bars
            bars = self.client.get_stock_bars(request)
            
            # Check if symbol is in response
            if not bars or symbol not in bars:
                logger.warning(f"No data returned for {symbol}")
                return []
                
            # Format candles
            candles = [self._format_candle(symbol, bar) for bar in bars[symbol]]
            
            # Sort by timestamp (newest last)
            candles.sort(key=lambda x: x['timestamp'])
            
            return candles
        except Exception as e:
            logger.error(f"Error getting candles for {symbol}: {e}")
            return []
            
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a symbol.
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Latest price or None if not available
        """
        # Get the latest candle
        candles = self.get_candles(symbol, '1m', limit=1)
        
        if candles and len(candles) > 0:
            return candles[-1]['close']
            
        return None
        
    def get_daily_candles(
        self,
        symbol: str,
        days: int = 30,
        end: Optional[Union[str, datetime]] = None
    ) -> List[Dict]:
        """
        Get daily candle data for a symbol.
        
        Args:
            symbol: Symbol to get data for
            days: Number of days of history
            end: End date/time (optional)
            
        Returns:
            List of daily candle dictionaries
        """
        return self.get_candles(symbol, '1d', limit=days, end=end)
        
    def get_minute_candles(
        self,
        symbol: str,
        minutes: int = 60,
        end: Optional[Union[str, datetime]] = None
    ) -> List[Dict]:
        """
        Get minute candle data for a symbol.
        
        Args:
            symbol: Symbol to get data for
            minutes: Number of minutes of history
            end: End date/time (optional)
            
        Returns:
            List of minute candle dictionaries
        """
        return self.get_candles(symbol, '1m', limit=minutes, end=end)
        
    def get_multiple_symbols(
        self,
        symbols: List[str],
        timeframe: str = '5m',
        limit: int = 20
    ) -> Dict[str, List[Dict]]:
        """
        Get candle data for multiple symbols.
        
        Args:
            symbols: Symbols to get data for
            timeframe: Candle timeframe
            limit: Maximum number of candles per symbol
            
        Returns:
            Dictionary mapping symbols to candle lists
        """
        result = {}
        for symbol in symbols:
            result[symbol] = self.get_candles(symbol, timeframe, limit=limit)
            
        return result

# Global instance
_historical_data_provider = HistoricalDataProvider()

def get_history_provider() -> HistoricalDataProvider:
    """
    Get the global historical data provider instance.
    
    Returns:
        HistoricalDataProvider instance
    """
    return _historical_data_provider

def get_candles(
    symbol: str,
    timeframe: str = '5m',
    start: Optional[Union[str, datetime]] = None,
    end: Optional[Union[str, datetime]] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Get historical candle data for a symbol.
    
    This is a convenience function that uses the global provider instance.
    
    Args:
        symbol: Symbol to get data for
        timeframe: Candle timeframe (e.g., '1m', '5m', '1h', '1d')
        start: Start date/time (optional)
        end: End date/time (optional)
        limit: Maximum number of candles to return
        
    Returns:
        List of candle dictionaries
    """
    provider = get_history_provider()
    return provider.get_candles(symbol, timeframe, start, end, limit)

def get_latest_price(symbol: str) -> Optional[float]:
    """
    Get the latest price for a symbol.
    
    This is a convenience function that uses the global provider instance.
    
    Args:
        symbol: Symbol to get price for
        
    Returns:
        Latest price or None if not available
    """
    provider = get_history_provider()
    return provider.get_latest_price(symbol)