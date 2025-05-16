"""
Historical Market Data Provider Module

This module provides access to historical market data via Alpaca API.
It provides candle data at various timeframes for technical analysis.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from common.redis_utils import get_redis_client

logger = logging.getLogger(__name__)

# Redis event channels
CANDLE_UPDATE_CHANNEL = "market.candle_update"

# Cache configuration
CACHE_EXPIRY = 60  # seconds

class HistoricalDataProvider:
    """Provider for historical market data."""
    def __init__(self, api_key=None, api_secret=None):
        """
        Initialize the historical data provider.
        
        Args:
            api_key: Alpaca API key (default: from environment)
            api_secret: Alpaca API secret (default: from environment)
        """
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self.api_secret = api_secret or os.environ.get("ALPACA_API_SECRET")
        
        # Initialize Redis client for event publishing
        self.redis = get_redis_client()
        
        self.client = StockHistoricalDataClient(self.api_key, self.api_secret)
        
        # Cache for recently requested data
        self._cache = {}
        
    def get_candles(self, symbol: str, timeframe: str, limit: int = 100, 
                   end: Optional[datetime] = None) -> List[Dict]:
        """
        Get historical candle data for a symbol.
        
        Args:
            symbol: The ticker symbol
            timeframe: One of "1m", "5m", "10m", "15m", "30m", "1h", "1d"
            limit: Number of candles to return
            end: End datetime (defaults to now)
            
        Returns:
            List of candle data (OHLCV)
        """
        # Convert symbol to uppercase
        symbol = symbol.upper()
        
        # Default end time is now
        if not end:
            end = datetime.now()
            
        # Calculate start time based on limit and timeframe
        start = self._calculate_start_time(end, timeframe, limit)
        
        # Check cache
        cache_key = f"{symbol}_{timeframe}_{start.isoformat()}_{end.isoformat()}"
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            # Check if cache is still valid
            if datetime.now() < cache_entry['expires']:
                logger.debug(f"Cache hit for {cache_key}")
                return cache_entry['data']
        
        # Convert timeframe string to TimeFrame enum
        tf, multiplier = self._parse_timeframe(timeframe)
        
        # Create request
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
            adjustment='raw'  # Use raw data without adjustments
        )
        
        try:
            bars = self.client.get_stock_bars(request_params)
            
            # Format the results
            if symbol in bars.data:
                result = self._format_bars(bars.data[symbol])
                
                # Update cache
                self._cache[cache_key] = {
                    'data': result,
                    'expires': datetime.now() + timedelta(seconds=CACHE_EXPIRY)
                }
                
                # Publish candle update event to Redis
                if self.redis and self.redis.available:
                    candle_event = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "candles": result[:5],  # Only send the most recent candles to reduce payload size
                        "candle_count": len(result),
                        "start_time": start.isoformat(),
                        "end_time": end.isoformat(),
                        "event_type": "candle_update",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Publish to global candle update channel
                    self.redis.publish(CANDLE_UPDATE_CHANNEL, json.dumps(candle_event))
                    # Publish to ticker-specific channel
                    self.redis.publish(f"ticker.{symbol}.candles", json.dumps(candle_event))
                    logger.debug(f"Published candle update event for {symbol} ({timeframe})")
                
                return result
            else:
                logger.warning(f"No data returned for {symbol} with timeframe {timeframe}")
                return []
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []
    
    def _parse_timeframe(self, timeframe: str) -> tuple:
        """
        Parse a timeframe string to Alpaca TimeFrame enum.
        
        Args:
            timeframe: One of "1m", "5m", "10m", "15m", "30m", "1h", "1d"
            
        Returns:
            tuple: (TimeFrame, multiplier)
        """
        if timeframe == "1m":
            return TimeFrame.Minute, 1
        elif timeframe == "5m":
            return TimeFrame.Minute, 5
        elif timeframe == "10m":
            return TimeFrame.Minute, 10
        elif timeframe == "15m":
            return TimeFrame.Minute, 15
        elif timeframe == "30m":
            return TimeFrame.Minute, 30
        elif timeframe == "1h":
            return TimeFrame.Hour, 1
        elif timeframe == "1d":
            return TimeFrame.Day, 1
        else:
            logger.warning(f"Unsupported timeframe: {timeframe}, falling back to 1m")
            return TimeFrame.Minute, 1
    
    def _calculate_start_time(self, end: datetime, timeframe: str, limit: int) -> datetime:
        """
        Calculate the start time based on end time, timeframe, and limit.
        
        Args:
            end: End datetime
            timeframe: Timeframe string
            limit: Number of bars
            
        Returns:
            datetime: Start time
        """
        if timeframe == "1m":
            delta = timedelta(minutes=limit)
        elif timeframe == "5m":
            delta = timedelta(minutes=5 * limit)
        elif timeframe == "10m":
            delta = timedelta(minutes=10 * limit)
        elif timeframe == "15m":
            delta = timedelta(minutes=15 * limit)
        elif timeframe == "30m":
            delta = timedelta(minutes=30 * limit)
        elif timeframe == "1h":
            delta = timedelta(hours=limit)
        elif timeframe == "1d":
            delta = timedelta(days=limit)
        else:
            delta = timedelta(minutes=limit)
            
        # Extend by 20% to account for market hours, weekends, etc.
        delta = delta * 1.2
        
        return end - delta
    
    def _format_bars(self, bars) -> List[Dict]:
        """
        Format bar data for API response.
        
        Args:
            bars: Alpaca bar data
            
        Returns:
            list: Formatted candle data
        """
        return [
            {
                "time": bar.timestamp.isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume)
            }
            for bar in bars
        ]
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache = {}
        logger.info("Historical data cache cleared")

# Singleton instance
_historical_data_provider = None

def get_historical_data_provider() -> HistoricalDataProvider:
    """
    Get the global historical data provider instance.
    
    Returns:
        HistoricalDataProvider: Global historical data provider instance
    """
    global _historical_data_provider
    if _historical_data_provider is None:
        _historical_data_provider = HistoricalDataProvider()
    return _historical_data_provider