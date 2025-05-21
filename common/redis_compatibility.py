"""
Redis Compatibility Layer

This module provides Redis-compatible interfaces that actually use PostgreSQL
as the backend. This allows existing code to work without changes while
we complete the migration from Redis to PostgreSQL.
"""

import logging
import json
from typing import Dict, Any, List, Callable, Optional, Union
from datetime import datetime

from .events import (
    publish_event, 
    poll_events, 
    get_latest_event_id, 
    update_price_cache, 
    get_price_from_cache,
    clear_price_cache,
    get_status,
    EventChannels
)

# Configure logging
logger = logging.getLogger(__name__)

# Define standard event channels - using the same names as before
# for backward compatibility
class RedisEventChannels:
    """Standard event channels used throughout the application."""
    SETUP_RECEIVED = "setup.received"
    SETUP_PARSED = "setup.parsed"
    MARKET_PRICE_UPDATE = "market.price_update"
    SIGNAL_TRIGGERED = "signal.triggered"
    TRADE_EXECUTED = "trade.executed"
    POSITION_UPDATED = "position.updated"
    POSITION_CLOSED = "position.closed"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    
    # Channel mapping from old Redis channels to new PostgreSQL channels
    _CHANNEL_MAP = {
        SETUP_RECEIVED: EventChannels.SETUP_CREATED,
        SETUP_PARSED: EventChannels.SETUP_UPDATED,
        MARKET_PRICE_UPDATE: EventChannels.MARKET_PRICE_UPDATE,
        SIGNAL_TRIGGERED: EventChannels.SIGNAL_TRIGGERED,
        TRADE_EXECUTED: EventChannels.TRADE_EXECUTED,
        POSITION_UPDATED: EventChannels.TRADE_UPDATED,
        POSITION_CLOSED: EventChannels.TRADE_CLOSED,
        ERROR: "system:error",
        WARNING: "system:warning",
        INFO: "system:info"
    }
    
    @classmethod
    def map_channel(cls, channel: str) -> str:
        """Map an old Redis channel to a new PostgreSQL channel."""
        return cls._CHANNEL_MAP.get(channel, channel)

# Redis client compatibility class that uses PostgreSQL
class RedisClient:
    """
    Redis-compatible client that uses PostgreSQL for storage.
    
    This class provides a transition layer that looks like Redis but
    actually uses PostgreSQL for all operations.
    """
    
    def __init__(self, redis_url=None):
        """Initialize the PostgreSQL-based Redis client."""
        self._health = {
            'connected': True,
            'backend': 'PostgreSQL',
            'last_operation': datetime.utcnow().isoformat()
        }
        logger.info("Using PostgreSQL-based Redis compatibility layer")
        
    def ping(self) -> bool:
        """
        Check if the database is available.
        
        Returns:
            bool: True if the database is available, False otherwise
        """
        # Return the status of the PostgreSQL connection from events.py
        status = get_status()
        return status.get('connected', False)
        
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """
        Publish an event to a channel.
        
        Args:
            channel: The channel to publish to
            data: The event data
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Map old channel name to new channel name if needed
        pg_channel = RedisEventChannels.map_channel(channel)
        
        # Publish to the PostgreSQL event system
        return publish_event(pg_channel, data)
        
    def get(self, key: str) -> Optional[str]:
        """
        Get a value from the cache.
        
        Args:
            key: The key to get
            
        Returns:
            Optional[str]: The value or None if not found
        """
        # For price cache keys, use the price cache
        if key.startswith('price:'):
            ticker = key.split(':')[1]
            price_data = get_price_from_cache(ticker)
            if price_data:
                return json.dumps(price_data)
            return None
        
        # For other keys, not implemented
        logger.warning(f"Redis GET operation not implemented for key: {key}")
        return None
        
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The key to set
            value: The value to set
            ex: Optional expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        # For price cache keys, use the price cache
        if key.startswith('price:'):
            ticker = key.split(':')[1]
            try:
                price_data = json.loads(value)
                price = price_data.get('price', 0.0)
                return update_price_cache(ticker, price)
            except Exception as e:
                logger.error(f"Error setting price cache: {e}")
                return False
        
        # For other keys, not implemented
        logger.warning(f"Redis SET operation not implemented for key: {key}")
        return False
        
    def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: The pattern to match
            
        Returns:
            List[str]: List of matching keys
        """
        # Not fully implemented yet
        logger.warning(f"Redis KEYS operation not fully implemented for pattern: {pattern}")
        return []
        
    def delete(self, *keys) -> int:
        """
        Delete keys from the cache.
        
        Args:
            *keys: The keys to delete
            
        Returns:
            int: Number of keys deleted
        """
        # For price cache keys, clear the price cache
        price_keys = [k for k in keys if isinstance(k, str) and k.startswith('price:')]
        if price_keys and clear_price_cache():
            return len(price_keys)
            
        # For other keys, not implemented
        logger.warning(f"Redis DELETE operation not implemented for keys: {keys}")
        return 0

    @property
    def client(self):
        """Get the underlying client (self for compatibility)."""
        return self

# Create a global instance for backward compatibility
redis_client = RedisClient()

# Redis event manager that uses PostgreSQL
class RedisEventManager:
    """
    Redis event manager compatibility class that uses PostgreSQL.
    
    This class provides a transition layer that looks like the Redis event manager
    but actually uses PostgreSQL for all operations.
    """
    
    def __init__(self):
        """Initialize the PostgreSQL-based event manager."""
        self._client = redis_client
        self._running = True
        self._message_counters = {
            'received': 0,
            'processed': 0,
            'errors': 0
        }
        
    def start(self) -> bool:
        """
        Start the event manager.
        
        Returns:
            bool: True if successful, False otherwise
        """
        self._running = True
        return True
        
    def stop(self) -> bool:
        """
        Stop the event manager.
        
        Returns:
            bool: True if successful, False otherwise
        """
        self._running = False
        return True
        
    def get_health(self) -> Dict[str, Any]:
        """
        Get the health status of the event manager.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            'running': self._running,
            'connected': True,
            'backend': 'PostgreSQL',
            'messages': self._message_counters,
            'last_check': datetime.utcnow().isoformat()
        }
        
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """
        Publish an event to a channel.
        
        Args:
            channel: The channel to publish to
            data: The event data
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self._client.publish(channel, data)

# Functions for backward compatibility

def get_redis_client() -> RedisClient:
    """
    Get the Redis client singleton.
    
    Returns:
        RedisClient: PostgreSQL-based Redis client
    """
    return redis_client

def ping_redis() -> bool:
    """
    Check if Redis is available.
    
    Returns:
        bool: True if available
    """
    return redis_client.ping()

def ensure_redis_is_running() -> bool:
    """
    Ensure Redis is running and available.
    
    Returns:
        bool: True if Redis is available
    """
    return ping_redis()