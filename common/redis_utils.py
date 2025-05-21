"""
Dummy Redis Replacement

This module provides a dummy Redis replacement that doesn't depend on any actual Redis connection.
It allows the code to run without Redis by providing the minimal interface needed.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

# Configure logging
logger = logging.getLogger(__name__)

# Event channel definitions
class EventChannels:
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

class DummyRedisClient:
    """
    Dummy Redis client that logs operations but doesn't actually use Redis.
    """
    
    def __init__(self):
        """Initialize the dummy Redis client."""
        logger.info("Using Dummy Redis client (no actual Redis connection)")
        
    def ping(self) -> bool:
        """
        Pretend to check if Redis is available.
        
        Returns:
            bool: Always True
        """
        return True
        
    def publish(self, channel: str, data: Any) -> bool:
        """
        Pretend to publish an event to a channel.
        
        Args:
            channel: The channel to publish to
            data: The event data
            
        Returns:
            bool: Always True
        """
        logger.debug(f"Would publish to {channel}: {data}")
        return True
        
    def subscribe(self, channel: str, callback: Callable) -> bool:
        """
        Pretend to subscribe to a channel.
        
        Args:
            channel: The channel to subscribe to
            callback: The callback function
            
        Returns:
            bool: Always True
        """
        logger.debug(f"Would subscribe to {channel}")
        return True
        
    def set(self, key: str, value: Any, expiration: int = 3600) -> bool:
        """
        Pretend to set a value in the cache.
        
        Args:
            key: The key to set
            value: The value to set
            expiration: Time in seconds until the key expires
            
        Returns:
            bool: Always True
        """
        logger.debug(f"Would set {key} to {value} (expiration: {expiration}s)")
        return True
        
    def get(self, key: str) -> Optional[Any]:
        """
        Pretend to get a value from the cache.
        
        Args:
            key: The key to get
            
        Returns:
            None (always)
        """
        logger.debug(f"Would get {key}")
        return None
        
    def delete(self, key: str) -> bool:
        """
        Pretend to delete a value from the cache.
        
        Args:
            key: The key to delete
            
        Returns:
            bool: Always True
        """
        logger.debug(f"Would delete {key}")
        return True

# Global singleton instance
redis_client = DummyRedisClient()

def get_redis_client():
    """Get the Redis client singleton."""
    global redis_client
    return redis_client

def ping_redis():
    """Check if Redis is available."""
    return True

def ensure_redis_is_running():
    """Ensure Redis is running."""
    return True

def publish_event(channel, data):
    """Publish an event to a channel."""
    if isinstance(data, dict) and 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    return redis_client.publish(channel, data)

def subscribe_to_channel(channel, callback):
    """Subscribe to a channel."""
    return redis_client.subscribe(channel, callback)

class RedisClient(DummyRedisClient):
    """Redis client class for backward compatibility."""
    pass

class RedisEventManager:
    """Redis event manager for backward compatibility."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisEventManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the event manager."""
        self._client = redis_client
        self._running = True
        self._message_counters = {'received': 0, 'processed': 0, 'errors': 0}
    
    def start(self):
        """Start the event manager."""
        self._running = True
        return True
    
    def stop(self):
        """Stop the event manager."""
        self._running = False
        return True
    
    def subscribe(self, channel, callback):
        """Subscribe to a channel."""
        return redis_client.subscribe(channel, callback)
    
    def unsubscribe(self, channel, callback=None):
        """Unsubscribe from a channel."""
        return True
    
    def publish(self, channel, data):
        """Publish an event to a channel."""
        return publish_event(channel, data)
    
    def get_health(self):
        """Get the health status of the event manager."""
        return {
            'healthy': True,
            'running': self._running,
            'counters': self._message_counters,
            'last_check': datetime.now().isoformat()
        }