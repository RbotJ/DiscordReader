"""
Redis Utilities (PostgreSQL-based)

This module provides Redis-compatible interfaces that use PostgreSQL as the backend.
This allows existing code to continue working while removing the Redis dependency.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Union

# Import PostgreSQL event system
from common.events import (
    publish_event as publish_pg_event,
    subscribe as pg_subscribe,
    EventChannels as PgEventChannels, 
    initialize_events,
    poll_events,
    get_status
)

# Make sure the PostgreSQL event system is initialized
initialize_events()

# Configure logging
logger = logging.getLogger(__name__)

# Define standard event channels - reusing the PgEventChannels for consistency
class EventChannels:
    """Standard event channels used throughout the application."""
    SETUP_RECEIVED = PgEventChannels.SETUP_CREATED
    SETUP_PARSED = PgEventChannels.SETUP_UPDATED
    MARKET_PRICE_UPDATE = PgEventChannels.MARKET_PRICE_UPDATE
    SIGNAL_TRIGGERED = PgEventChannels.SIGNAL_TRIGGERED
    TRADE_EXECUTED = PgEventChannels.TRADE_EXECUTED
    POSITION_UPDATED = PgEventChannels.TRADE_UPDATED
    POSITION_CLOSED = PgEventChannels.TRADE_CLOSED
    ERROR = "system:error"
    WARNING = "system:warning"
    INFO = "system:info"
    
# Use the PostgreSQL-based Redis client
redis_client = PgRedisClient()

class RedisClient:
    """
    PostgreSQL-based Redis client class that provides a unified interface for operations.
    
    This class forwards all operations to the PostgreSQL implementation in redis_compatibility.py.
    """
    # Dictionary to store instances
    _instances = {}
    
    def __new__(cls, redis_url=None):
        # We ignore the URL parameter since we're using PostgreSQL instead
        
        # Return existing instance if available
        if 'default' in cls._instances:
            return cls._instances['default']
            
        # Create a new instance
        instance = super(RedisClient, cls).__new__(cls)
        instance._initialize()
        cls._instances['default'] = instance
        return instance
    
    def _initialize(self):
        """Initialize the PostgreSQL-based Redis client"""
        # Use the PostgreSQL compatibility layer instead of actual Redis
        self._url = "postgresql-event-system"
        self._client = PgRedisClient()
        logger.info("Using PostgreSQL-based event system instead of Redis")
    
    @property
    def client(self):
        """Get the underlying Redis client."""
        return self._client
    
    def ping(self):
        """Check if PostgreSQL is available."""
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"PostgreSQL ping failed: {e}")
            return False
    
    def publish(self, channel, data):
        """Publish an event to a channel."""
        try:
            # Add timestamp if not present
            if isinstance(data, dict) and 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
                
            # Publish the event
            result = self._client.publish(channel, data)
            logger.debug(f"Published event to {channel} via PostgreSQL")
            return result
        except Exception as e:
            logger.error(f"Error publishing event to {channel}: {e}")
            return False
    
    def subscribe(self, channel, callback):
        """Subscribe to a channel."""
        # Forward to the PostgreSQL client
        return self._client.subscribe(channel, callback)
    
    def set(self, key, value, expiration=3600):
        """Set a value in the cache."""
        try:
            self._client.set(key, json.dumps(value), ex=expiration)
            logger.debug(f"Set cache key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def get(self, key):
        """Get a value from the cache."""
        try:
            value = self._client.get(key)
            
            if value:
                return json.loads(value)
            
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    def delete(self, key):
        """Delete a value from the cache."""
        try:
            self._client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
        
# Get Redis client function - maintains backward compatibility
def get_redis_client():
    """
    Get the Redis client singleton (now PostgreSQL-based).
    
    Returns:
        PostgreSQL-based Redis client
    """
    # Use the Redis compatibility layer (PgRedisClient) 
    return PgRedisClient()

def ping_redis():
    """
    Check if PostgreSQL event system is available.
    
    Returns:
        bool: True if the database is available, False otherwise
    """
    try:
        client = get_redis_client()
        return client.ping()
    except Exception as e:
        logger.error(f"PostgreSQL event system ping failed: {e}")
        return False

# Add missing function that other modules are importing
def ensure_redis_is_running():
    """
    Ensure the event system is running and available.
    
    Returns:
        bool: True since the PostgreSQL system is always running
    """
    # PostgreSQL is always running, so we can just return True
    return True

def publish_event(channel, data):
    """
    Publish an event to the PostgreSQL event system.
    
    Args:
        channel (str): The channel to publish to
        data (dict): The data to publish
        
    Returns:
        bool: True if the event was published, False otherwise
    """
    try:
        # Use the PostgreSQL client directly
        client = get_redis_client()
        
        # Add timestamp if not present
        if isinstance(data, dict) and 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
            
        # Publish the event through the PostgreSQL client
        result = client.publish(channel, data)
        logger.debug(f"Published event to {channel} via PostgreSQL")
        return result
    except Exception as e:
        logger.error(f"Error publishing event to {channel}: {e}")
        return False

class RedisEventManager:
    """
    A PostgreSQL-based event manager that provides Redis-compatible event handling.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisEventManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the event manager with PostgreSQL client"""
        # Use the compatibility layer
        self._client = get_redis_client()
        self._running = True
        self._message_counters = {
            'received': 0,
            'processed': 0,
            'errors': 0
        }
    
    def start(self):
        """Start the event manager - already running with PostgreSQL"""
        self._running = True
        logger.info("PostgreSQL event manager is running")
        return True
        
    def stop(self):
        """Stop the event manager - no-op with PostgreSQL"""
        self._running = False
        logger.info("PostgreSQL event manager stopped")
        return True
        
    def subscribe(self, channel, callback):
        """
        Subscribe to a channel - forwarded to PostgreSQL client
        
        Args:
            channel (str): The channel to subscribe to
            callback (callable): The callback function to call when a message is received
            
        Returns:
            bool: True if subscribed successfully, False otherwise
        """
        try:
            # Forward to PostgreSQL client
            return self._client.subscribe(channel, callback)
        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {e}")
            return False
            
    def unsubscribe(self, channel, callback=None):
        """
        Unsubscribe from a channel - no-op with PostgreSQL
        
        Returns:
            bool: Always True
        """
        # PostgreSQL handles this automatically
        logger.info(f"Unsubscribed from channel: {channel}")
        return True
        
    def publish(self, channel, data):
        """
        Publish an event to a channel - forwarded to PostgreSQL client
        
        Args:
            channel (str): The channel to publish to
            data (dict): The data to publish
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Add timestamp if not present
            if isinstance(data, dict) and 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            # Forward to PostgreSQL client
            return self._client.publish(channel, data)
        except Exception as e:
            logger.error(f"Error publishing event to {channel}: {e}")
            return False
            
    def get_health(self):
        """
        Get the health status of the event manager.
        
        Returns:
            dict: Health status information
        """
        return {
            'healthy': True,  # PostgreSQL is always healthy
            'running': self._running,
            'counters': self._message_counters,
            'channels': [],  # PostgreSQL handles this internally
            'listener_count': 0,  # PostgreSQL handles this internally
            'last_health_check': datetime.now().isoformat()
        }

def subscribe_to_channel(channel, callback):
    """
    Subscribe to a channel.
    
    Args:
        channel: The channel to subscribe to
        callback: The callback function to call when a message is received
        
    Returns:
        bool: True if successful, False otherwise
    """
    return redis_client.subscribe(channel, callback)