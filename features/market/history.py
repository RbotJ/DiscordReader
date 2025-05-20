"""
Historical Market Data Module

This module provides access to historical market data for stocks and options
using the Alpaca API. It handles data fetching, caching, and transformation.
"""
import os
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta, date
import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import Adjustment
from alpaca.common.exceptions import APIError

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

# Dictionary to map timeframe strings to TimeFrame objects
TIMEFRAMES = {
    '1m': TimeFrame(1, TimeFrameUnit.Minute),
    '5m': TimeFrame(5, TimeFrameUnit.Minute),
    '15m': TimeFrame(15, TimeFrameUnit.Minute),
    '30m': TimeFrame(30, TimeFrameUnit.Minute),
    '1h': TimeFrame(1, TimeFrameUnit.Hour),
    '1d': TimeFrame(1, TimeFrameUnit.Day),
    # Legacy format support
    '1Min': TimeFrame(1, TimeFrameUnit.Minute),
    '5Min': TimeFrame(5, TimeFrameUnit.Minute),
    '15Min': TimeFrame(15, TimeFrameUnit.Minute),
    '30Min': TimeFrame(30, TimeFrameUnit.Minute),
    '1Hour': TimeFrame(1, TimeFrameUnit.Hour),
    '1Day': TimeFrame(1, TimeFrameUnit.Day),
}

class MarketHistoryProvider:
    """
    Provider for historical market data using Alpaca API.
    """
    
    def __init__(self):
        """Initialize the market history provider."""
        self.client = None
        self.initialized = False
        self.data_cache = {}  # Simple in-memory cache
        
        # Initialize client
        self._initialize_client()
        
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
            self.initialized = True
            logger.info("Historical data client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing historical data client: {e}")
            return False
            
    def get_bars(
        self,
        symbol: str,
        timeframe: str = '5m',
        start: Optional[Union[datetime, date, str]] = None,
        end: Optional[Union[datetime, date, str]] = None,
        limit: int = 100,
        adjustment: str = 'all'
    ) -> Optional[pd.DataFrame]:
        """
        Get historical bars for a symbol.
        
        Args:
            symbol: Ticker symbol
            timeframe: Bar timeframe (e.g., '1m', '5m', '1d')
            start: Start date/time (optional)
            end: End date/time (optional)
            limit: Maximum number of bars to return
            adjustment: Price adjustment ('raw', 'split', 'dividend', 'all')
            
        Returns:
            DataFrame with bar data or None on error
        """
        if not self.initialized or not self.client:
            logger.warning("Historical data client not initialized")
            return None
            
        # Process timeframe
        tf = TIMEFRAMES.get(timeframe)
        if not tf:
            logger.warning(f"Invalid timeframe: {timeframe}, using 5m")
            tf = TIMEFRAMES['5m']
            
        # Process start and end dates
        now = datetime.now()
        
        if end is None:
            end = now
        elif isinstance(end, str):
            try:
                # Try to parse as datetime
                end = datetime.fromisoformat(end.replace('Z', '+00:00'))
            except ValueError:
                # Try to parse as date
                try:
                    end = datetime.strptime(end, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Invalid end date: {end}, using current time")
                    end = now
        elif isinstance(end, date) and not isinstance(end, datetime):
            # Convert date to datetime
            end = datetime.combine(end, datetime.min.time())
            
        if start is None:
            # Default to appropriate lookback based on timeframe
            if timeframe in ['1m', '1Min']:
                start = end - timedelta(days=1)  # 1 day for 1-minute bars
            elif timeframe in ['5m', '5Min']:
                start = end - timedelta(days=5)  # 5 days for 5-minute bars
            elif timeframe in ['15m', '15Min', '30m', '30Min']:
                start = end - timedelta(days=10)  # 10 days for 15/30-minute bars
            elif timeframe in ['1h', '1Hour']:
                start = end - timedelta(days=30)  # 30 days for hourly bars
            else:
                start = end - timedelta(days=365)  # 1 year for daily bars
        elif isinstance(start, str):
            try:
                # Try to parse as datetime
                start = datetime.fromisoformat(start.replace('Z', '+00:00'))
            except ValueError:
                # Try to parse as date
                try:
                    start = datetime.strptime(start, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Invalid start date: {start}, using default lookback")
                    start = end - timedelta(days=30)
        elif isinstance(start, date) and not isinstance(start, datetime):
            # Convert date to datetime
            start = datetime.combine(start, datetime.min.time())
            
        # Check cache
        cache_key = f"{symbol}_{timeframe}_{start.isoformat()}_{end.isoformat()}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        # Process adjustment
        adj = Adjustment.ALL
        if adjustment.lower() == 'raw':
            adj = Adjustment.RAW
        elif adjustment.lower() == 'split':
            adj = Adjustment.SPLIT
        elif adjustment.lower() == 'dividend':
            adj = Adjustment.DIVIDEND
            
        try:
            # Create request
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                limit=limit,
                adjustment=adj
            )
            
            # Get bars
            response = self.client.get_stock_bars(request)
            
            # Check if we got a response for our symbol
            if not response or symbol not in response:
                logger.warning(f"No data returned for {symbol}")
                return None
                
            # Convert to DataFrame
            df = response[symbol].df
            
            # Cache the result
            self.data_cache[cache_key] = df
            
            return df
        except APIError as e:
            logger.error(f"API error getting bars for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {e}", exc_info=True)
            return None
            
    def get_candles(
        self,
        symbol: str,
        timeframe: str = '5m',
        start: Optional[Union[datetime, date, str]] = None,
        end: Optional[Union[datetime, date, str]] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get historical candles for a symbol in a format suitable for charting.
        
        Args:
            symbol: Ticker symbol
            timeframe: Candle timeframe (e.g., '1m', '5m', '1d')
            start: Start date/time (optional)
            end: End date/time (optional)
            limit: Maximum number of candles to return
            
        Returns:
            List of candle dictionaries or None on error
        """
        # Get bars as DataFrame
        df = self.get_bars(symbol, timeframe, start, end, limit)
        if df is None or df.empty:
            return None
            
        # Convert to list of dictionaries
        candles = []
        for timestamp, row in df.iterrows():
            candle = {
                'timestamp': timestamp.isoformat(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume'])
            }
            candles.append(candle)
            
        return candles
        
    def get_daily_bars(
        self,
        symbol: str,
        start: Optional[Union[date, str]] = None,
        end: Optional[Union[date, str]] = None,
        limit: int = 252  # ~1 year of trading days
    ) -> Optional[pd.DataFrame]:
        """
        Get daily bars for a symbol.
        
        Args:
            symbol: Ticker symbol
            start: Start date (optional)
            end: End date (optional)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with daily bar data or None on error
        """
        return self.get_bars(symbol, '1d', start, end, limit)
        
    def get_intraday_bars(
        self,
        symbol: str,
        timeframe: str = '5m',
        days: int = 5,
        end: Optional[Union[datetime, date, str]] = None,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Get intraday bars for a symbol for the specified number of days.
        
        Args:
            symbol: Ticker symbol
            timeframe: Bar timeframe (e.g., '1m', '5m', '1h')
            days: Number of days to look back
            end: End date/time (optional, defaults to now)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with intraday bar data or None on error
        """
        # Calculate start date based on days
        if end is None:
            end = datetime.now()
        elif isinstance(end, str):
            try:
                end = datetime.fromisoformat(end.replace('Z', '+00:00'))
            except ValueError:
                try:
                    end = datetime.strptime(end, '%Y-%m-%d')
                except ValueError:
                    end = datetime.now()
        elif isinstance(end, date) and not isinstance(end, datetime):
            end = datetime.combine(end, datetime.min.time())
            
        start = end - timedelta(days=days)
        
        return self.get_bars(symbol, timeframe, start, end, limit)
        
    def clear_cache(self):
        """Clear the data cache."""
        self.data_cache = {}
        logger.info("Historical data cache cleared")

# Global instance
history_provider = MarketHistoryProvider()

def get_history_provider() -> MarketHistoryProvider:
    """
    Get the global market history provider instance.
    
    Returns:
        MarketHistoryProvider instance
    """
    return history_provider