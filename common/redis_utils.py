"""
Redis Compatibility Layer

This module provides a compatibility layer that maps Redis operations to our new
PostgreSQL-based caching and event system. This allows existing modules that
still import from redis_utils to continue working without modifications.

All Redis operations are redirected to equivalent PostgreSQL functions in events.py.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import json

# Import the new PostgreSQL-based functions
from common.events import (
    cache_data,
    get_from_cache,
    delete_from_cache,
    publish_event,
    subscribe_to_events,
    get_latest_event,
    update_price_cache,
    get_price_from_cache
)

logger = logging.getLogger(__name__)

# Compatibility layer for Redis client
class RedisClient:
    """Redis client compatibility class that maps to PostgreSQL functions."""
    
    def __init__(self, *args, **kwargs):
        logger.info("Initializing Redis compatibility layer (using PostgreSQL)")
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a value in the cache with optional expiration."""
        expiration = None
        if ex:
            expiration = datetime.utcnow() + timedelta(seconds=ex)
        
        # Convert to string if it's not already
        if not isinstance(value, str):
            value = json.dumps(value)
            
        return cache_data(key, value, expiration)
    
    def get(self, key: str) -> Optional[str]:
        """Get a value from the cache."""
        result = get_from_cache(key)
        if result is None:
            return None
        return result
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        return delete_from_cache(key)
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return get_from_cache(key) is not None
    
    def publish(self, channel: str, message: Any) -> bool:
        """Publish a message to a channel."""
        if not isinstance(message, str):
            message = json.dumps(message)
        return publish_event(channel, {"data": message})
    
    def hset(self, name: str, key: str, value: Any) -> bool:
        """Set a hash field to a value."""
        # For hash operations, we'll store as a JSON object under a single key
        hash_key = f"hash:{name}"
        
        # Get the current hash if it exists
        current = get_from_cache(hash_key)
        hash_data = {}
        
        if current:
            try:
                hash_data = json.loads(current)
            except:
                hash_data = {}
        
        # Update the hash with the new value
        hash_data[key] = value
        
        # Store the updated hash
        return cache_data(hash_key, json.dumps(hash_data))
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get the value of a hash field."""
        hash_key = f"hash:{name}"
        
        # Get the hash
        hash_data = get_from_cache(hash_key)
        if not hash_data:
            return None
        
        # Parse the hash and return the field value
        try:
            hash_dict = json.loads(hash_data)
            return hash_dict.get(key)
        except:
            return None
    
    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all the fields and values in a hash."""
        hash_key = f"hash:{name}"
        
        # Get the hash
        hash_data = get_from_cache(hash_key)
        if not hash_data:
            return {}
        
        # Parse the hash and return all fields
        try:
            return json.loads(hash_data)
        except:
            return {}

# Create a singleton instance
redis_client = RedisClient()

# Redis PubSub compatibility
class RedisPubSub:
    """Redis PubSub compatibility class that maps to PostgreSQL functions."""
    
    def __init__(self, **kwargs):
        self.subscribed_channels = []
        logger.info("Initializing Redis PubSub compatibility layer (using PostgreSQL)")
    
    def subscribe(self, *channels):
        """Subscribe to one or more channels."""
        for channel in channels:
            self.subscribed_channels.append(channel)
            subscribe_to_events(channel)
    
    def get_message(self, timeout=None):
        """Get a message from a subscribed channel."""
        if not self.subscribed_channels:
            return None
        
        # Get the latest event from any of the subscribed channels
        for channel in self.subscribed_channels:
            event = get_latest_event(channel)
            if event:
                return {
                    'type': 'message',
                    'channel': channel,
                    'data': event.get('data', '')
                }
        
        return None

# Factory functions for compatibility
def get_redis_client(*args, **kwargs) -> RedisClient:
    """Get a Redis client instance (compatibility layer)."""
    return redis_client

def create_pubsub() -> RedisPubSub:
    """Create a Redis PubSub instance (compatibility layer)."""
    return RedisPubSub()

# Price cache compatibility
def update_price_in_cache(ticker: str, price: float, timestamp=None) -> bool:
    """Update price in cache (compatibility layer)."""
    return update_price_cache(ticker, price, timestamp)

def get_cached_price(ticker: str) -> Optional[Dict[str, Any]]:
    """Get price from cache (compatibility layer)."""
    return get_price_from_cache(ticker)

# Initialize Redis compatibility layer
def init_redis_client() -> RedisClient:
    """Initialize the Redis client (compatibility layer)."""
    logger.info("Redis compatibility layer initialized (using PostgreSQL)")
    return redis_client

# Export the compatibility functions and classes
__all__ = [
    'RedisClient',
    'RedisPubSub', 
    'redis_client',
    'get_redis_client',
    'create_pubsub',
    'update_price_in_cache',
    'get_cached_price',
    'init_redis_client'
]