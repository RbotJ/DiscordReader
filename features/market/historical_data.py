"""
Historical Data Provider Module

This module provides historical market data for tracked symbols
and publishes candle updates to Redis channels.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from common.redis_utils import RedisClient
from features.alpaca.client import get_latest_bars, alpaca_market_client

# Configure logger
logger = logging.getLogger(__name__)

# Redis client for publishing candle updates
redis_client = RedisClient()

# Thread control variables
_data_thread = None
_thread_running = False

# Candle cache to avoid redundant updates
_candle_cache: Dict[str, Dict[str, Any]] = {}

def init_historical_data_provider() -> bool:
    """
    Initialize the historical data provider.
    
    Returns:
        bool: Success status
    """
    global _data_thread, _thread_running
    
    try:
        if not alpaca_market_client:
            logger.warning("Alpaca market client not initialized")
            return False
        
        # Check if data thread is already running
        if _data_thread and _data_thread.is_alive():
            logger.info("Historical data thread already running")
            return True
        
        # Start historical data thread
        _data_thread = threading.Thread(
            target=_historical_data_thread,
            daemon=True,
            name="HistoricalDataThread"
        )
        _thread_running = True
        _data_thread.start()
        
        # Wait a moment to ensure thread starts
        time.sleep(0.1)
        
        if _data_thread.is_alive():
            logger.info("Historical data thread started successfully")
            return True
        else:
            logger.error("Historical data thread failed to start")
            return False
    except Exception as e:
        logger.error(f"Error initializing historical data provider: {e}")
        return False

def _historical_data_thread() -> None:
    """Historical data thread function."""
    global _thread_running
    
    logger.info("Historical data thread started")
    
    # Track when we last checked each timeframe
    last_check = {
        '1Min': datetime.now() - timedelta(minutes=5),
        '5Min': datetime.now() - timedelta(minutes=20),
        '15Min': datetime.now() - timedelta(minutes=60),
        '1Hour': datetime.now() - timedelta(hours=4),
        '1Day': datetime.now() - timedelta(days=1)
    }
    
    while _thread_running:
        try:
            # Get active symbols from price monitor if available
            try:
                from features.market.price_monitor import get_monitored_symbols
                symbols = get_monitored_symbols()
            except ImportError:
                # Fallback to a sample list if price monitor is not available
                symbols = ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]
            
            if not symbols:
                # No symbols to monitor, sleep and check again
                time.sleep(10)
                continue
            
            now = datetime.now()
            
            # Check 1-minute candles every minute
            if now - last_check['1Min'] >= timedelta(minutes=1):
                _update_candles(symbols, '1Min', 10)
                last_check['1Min'] = now
            
            # Check 5-minute candles every 5 minutes
            if now - last_check['5Min'] >= timedelta(minutes=5):
                _update_candles(symbols, '5Min', 12)
                last_check['5Min'] = now
            
            # Check 15-minute candles every 15 minutes
            if now - last_check['15Min'] >= timedelta(minutes=15):
                _update_candles(symbols, '15Min', 16)
                last_check['15Min'] = now
            
            # Check hourly candles every hour
            if now - last_check['1Hour'] >= timedelta(hours=1):
                _update_candles(symbols, '1Hour', 24)
                last_check['1Hour'] = now
            
            # Check daily candles every day
            if now - last_check['1Day'] >= timedelta(hours=6):
                _update_candles(symbols, '1Day', 30)
                last_check['1Day'] = now
            
            # Sleep to avoid excessive API calls
            time.sleep(30)
        except Exception as e:
            logger.error(f"Error in historical data thread: {e}")
            time.sleep(60)  # Sleep longer on error
    
    logger.info("Historical data thread stopped")

def _update_candles(symbols: List[str], timeframe: str, limit: int) -> None:
    """
    Update candles for the given symbols and timeframe.
    
    Args:
        symbols: List of ticker symbols
        timeframe: Candle timeframe ('1Min', '5Min', '15Min', '1Hour', '1Day')
        limit: Number of candles to retrieve
    """
    try:
        # Map timeframe to Alpaca format
        alpaca_timeframe = timeframe
        if timeframe == '5Min':
            alpaca_timeframe = '5Min'
        elif timeframe == '15Min':
            alpaca_timeframe = '15Min'
        
        # Get latest bars for all symbols
        bars = get_latest_bars(symbols, alpaca_timeframe, limit)
        
        # Process bars for each symbol
        for symbol, symbol_bars in bars.items():
            if not symbol_bars:
                continue
            
            # Get the latest candle
            latest_candle = symbol_bars[-1]
            
            # Create cache key for this symbol and timeframe
            cache_key = f"{symbol}_{timeframe}"
            
            # Check if we already have this candle
            if (
                cache_key in _candle_cache and
                _candle_cache[cache_key].get('timestamp') == latest_candle.get('timestamp')
            ):
                # Skip if timestamps match (candle hasn't changed)
                continue
            
            # Update cache with latest candle
            _candle_cache[cache_key] = latest_candle
            
            # Create candle update with metadata
            candle_update = {
                'ticker': symbol,
                'timeframe': timeframe,
                'timestamp': latest_candle.get('timestamp'),
                'open': latest_candle.get('open'),
                'high': latest_candle.get('high'),
                'low': latest_candle.get('low'),
                'close': latest_candle.get('close'),
                'volume': latest_candle.get('volume'),
                'event_type': 'candle_update',
                'is_closed': True  # All historical candles are closed
            }
            
            # Publish to Redis channel for this symbol and timeframe
            redis_client.publish(f"candles:{symbol}:{timeframe}", candle_update)
            
            # Also publish to the general candle channel
            redis_client.publish("candles:all", candle_update)
            
            # Log candle update
            logger.debug(f"Published {timeframe} candle update for {symbol}")
    except Exception as e:
        logger.error(f"Error updating {timeframe} candles: {e}")

def get_historical_data(symbol: str, timeframe: str = '1Day', limit: int = 30) -> List[Dict[str, Any]]:
    """
    Get historical data for a symbol.
    
    Args:
        symbol: Ticker symbol
        timeframe: Candle timeframe (default: '1Day')
        limit: Number of candles to retrieve (default: 30)
        
    Returns:
        List of candle dictionaries
    """
    try:
        # Get latest bars
        bars = get_latest_bars([symbol], timeframe, limit)
        
        # Return the bars for this symbol
        if symbol in bars:
            return bars[symbol]
        else:
            return []
    except Exception as e:
        logger.error(f"Error getting historical data for {symbol}: {e}")
        return []

def shutdown() -> bool:
    """
    Shutdown the historical data provider.
    
    Returns:
        bool: Success status
    """
    global _thread_running, _data_thread
    
    try:
        # Signal thread to stop
        _thread_running = False
        
        # Wait for thread to stop (with timeout)
        if _data_thread and _data_thread.is_alive():
            _data_thread.join(timeout=5.0)
            
            if _data_thread.is_alive():
                logger.warning("Historical data thread did not stop gracefully")
                return False
        
        logger.info("Historical data provider shut down successfully")
        return True
    except Exception as e:
        logger.error(f"Error shutting down historical data provider: {e}")
        return False