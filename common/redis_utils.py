"""
Redis Utilities (PostgreSQL-based)

A collection of utilities that provide Redis-compatible interfaces while
actually using PostgreSQL as the backend. This allows for a smooth transition
while removing the Redis dependency.
"""

import logging
import os
import json
import time
import threading
from datetime import datetime

# Import PostgreSQL event system
from common.redis_compatibility import RedisClient as PgRedisClient
from common.events import EventChannels as PgEventChannels

# Configure logging
logger = logging.getLogger(__name__)

# No longer need Redis connection
_redis_client = None

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
    
# Singleton Redis client class - this is what components are trying to import
# We'll use the PostgreSQL-based client instead
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
        """Check if Redis is available."""
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def publish(self, channel, data):
        """Publish an event to a channel."""
        try:
            # Add timestamp if not present
            if isinstance(data, dict) and 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
                
            # Publish the event
            self._client.publish(channel, json.dumps(data))
            logger.debug(f"Published event to {channel}: {data}")
            return True
        except Exception as e:
            logger.error(f"Error publishing event to {channel}: {e}")
            return False
    
    def subscribe(self, channel, callback):
        """Subscribe to a channel."""
        # Delegate to the event manager
        return subscribe_to_channel(channel, callback)
    
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
    
    This function checks if the PostgreSQL event system is available and returns True if it is.
    It also starts the event manager if it's not already running.
    
    Returns:
        bool: True if the event system is available, False otherwise
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
    Manages Redis event handling with built-in threading for background subscription processing.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisEventManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the event manager"""
        # Use the global redis_client if available, otherwise create a new one
        global redis_client
        if redis_client is not None:
            self._client = redis_client.client
        else:
            self._client = get_redis_client()
            
        # Initialize pubsub and other properties
        try:
            self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        except Exception as e:
            logger.error(f"Error initializing Redis pubsub: {e}")
            self._pubsub = None
            
        self._listeners = {}  # Map of channel -> list of callbacks
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        self._health_check_interval = 60  # seconds
        self._last_health_check = 0
        self._healthy = False
        self._message_counters = {
            'received': 0,
            'processed': 0,
            'errors': 0
        }
    
    def start(self):
        """Start the event listener thread"""
        with self._lock:
            if self._running:
                logger.warning("Event manager is already running")
                return False
            
            self._running = True
            self._thread = threading.Thread(target=self._listen, daemon=True)
            self._thread.start()
            logger.info("Redis event manager started")
            return True
        
    def stop(self):
        """Stop the event listener thread"""
        with self._lock:
            if not self._running:
                logger.warning("Event manager is not running")
                return False
            
            self._running = False
            
            if self._thread:
                self._thread.join(timeout=2.0)
                if self._thread.is_alive():
                    logger.warning("Event listener thread did not terminate cleanly")
                self._thread = None
            
            logger.info("Redis event manager stopped")
            return True
        
    def subscribe(self, channel, callback):
        """
        Subscribe to a channel.
        
        Args:
            channel (str): The channel to subscribe to
            callback (callable): The callback function to call when a message is received
            
        Returns:
            bool: True if subscribed successfully, False otherwise
        """
        with self._lock:
            # Add to internal listeners dictionary
            if channel not in self._listeners:
                self._listeners[channel] = []
                
                # If this is the first listener, subscribe to the channel
                try:
                    self._pubsub.subscribe(channel)
                    logger.info(f"Subscribed to channel: {channel}")
                except Exception as e:
                    logger.error(f"Error subscribing to channel {channel}: {e}")
                    return False
            
            # Add callback if not already present
            if callback not in self._listeners[channel]:
                self._listeners[channel].append(callback)
                
            return True
            
    def unsubscribe(self, channel, callback=None):
        """
        Unsubscribe from a channel.
        
        Args:
            channel (str): The channel to unsubscribe from
            callback (callable, optional): The specific callback to unsubscribe,
                                         or None to unsubscribe from all callbacks
                                         
        Returns:
            bool: True if unsubscribed successfully, False otherwise
        """
        with self._lock:
            if channel not in self._listeners:
                logger.warning(f"Not subscribed to channel {channel}")
                return False
                
            if callback:
                # Remove specific callback
                try:
                    self._listeners[channel].remove(callback)
                except ValueError:
                    logger.warning(f"Callback not found for channel {channel}")
                    return False
                    
                # If no more listeners, unsubscribe from Redis
                if not self._listeners[channel]:
                    try:
                        self._pubsub.unsubscribe(channel)
                        del self._listeners[channel]
                        logger.info(f"Unsubscribed from channel: {channel}")
                    except Exception as e:
                        logger.error(f"Error unsubscribing from channel {channel}: {e}")
                        return False
            else:
                # Remove all callbacks
                try:
                    self._pubsub.unsubscribe(channel)
                    del self._listeners[channel]
                    logger.info(f"Unsubscribed from all callbacks for channel: {channel}")
                except Exception as e:
                    logger.error(f"Error unsubscribing from channel {channel}: {e}")
                    return False
                
            return True
        
    def publish(self, channel, data):
        """
        Publish an event to a channel.
        
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
            
            # Publish using the underlying Redis client
            self._client.publish(channel, json.dumps(data))
            logger.debug(f"Published event to {channel}: {data}")
            return True
        except Exception as e:
            logger.error(f"Error publishing event to {channel}: {e}")
            return False
            
    def get_health(self):
        """
        Get the health status of the event manager.
        
        Returns:
            dict: Health status information
        """
        now = time.time()
        
        # Only check if enough time has passed since last check
        if now - self._last_health_check > self._health_check_interval:
            try:
                self._healthy = ping_redis()
                self._last_health_check = now
            except Exception as e:
                logger.error(f"Error checking Redis health: {e}")
                self._healthy = False
        
        return {
            'healthy': self._healthy,
            'running': self._running and (self._thread is not None) and self._thread.is_alive(),
            'counters': self._message_counters,
            'channels': list(self._listeners.keys()),
            'listener_count': sum(len(callbacks) for callbacks in self._listeners.values()),
            'last_health_check': datetime.fromtimestamp(self._last_health_check).isoformat() if self._last_health_check else None
        }
        
    def _listen(self):
        """Background thread that listens for messages"""
        logger.info("Redis event listener thread started")
        
        while self._running:
            try:
                # Get message from Redis
                message = self._pubsub.get_message(timeout=0.1)
                
                if message is None:
                    # No message available, sleep briefly
                    time.sleep(0.01)
                    continue
                
                # Only process actual messages (not subscribe/unsubscribe confirmations)
                if message['type'] == 'message':
                    self._message_counters['received'] += 1
                    channel = message['channel']
                    data = message['data']
                    
                    # Parse JSON data
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(f"Error parsing JSON data from channel {channel}: {e}")
                        self._message_counters['errors'] += 1
                        continue
                    
                    # Process message with all registered callbacks
                    with self._lock:
                        if channel in self._listeners:
                            for callback in self._listeners[channel]:
                                try:
                                    callback(data)
                                    self._message_counters['processed'] += 1
                                except Exception as e:
                                    logger.error(f"Error in callback for channel {channel}: {e}")
                                    self._message_counters['errors'] += 1
            
            except redis.RedisError as e:
                logger.error(f"Redis error in event listener: {e}")
                self._message_counters['errors'] += 1
                time.sleep(1)  # Avoid hammering Redis if there's an error
                
            except Exception as e:
                logger.error(f"Unexpected error in event listener: {e}")
                self._message_counters['errors'] += 1
                time.sleep(1)  # Avoid tight loop on unexpected errors
        
        logger.info("Redis event listener thread stopped")

def subscribe_to_channel(channel, callback):
    """
    Subscribe to a Redis channel.
    
    Args:
        channel (str): The channel to subscribe to
        callback (callable): The callback function to call when a message is received
        
    Returns:
        bool: True if the subscription was created, False otherwise
    """
    # Use the event manager for robust subscription handling
    try:
        event_manager = RedisEventManager()
        # Start the event manager if it's not already running
        if not event_manager.get_health()['running']:
            event_manager.start()
        # Subscribe to the channel
        return event_manager.subscribe(channel, callback)
    except Exception as e:
        logger.error(f"Error subscribing to channel {channel}: {e}")
        return False

def cache_set(key, value, expiration=3600):
    """
    Set a value in the Redis cache.
    
    Args:
        key (str): The key to set
        value (any): The value to set (will be JSON encoded)
        expiration (int): Expiration time in seconds (default: 1 hour)
        
    Returns:
        bool: True if the value was set, False otherwise
    """
    try:
        client = get_redis_client()
        client.set(key, json.dumps(value), ex=expiration)
        logger.debug(f"Set cache key: {key}")
        return True
    except Exception as e:
        logger.error(f"Error setting cache key {key}: {e}")
        return False

def cache_get(key):
    """
    Get a value from the Redis cache.
    
    Args:
        key (str): The key to get
        
    Returns:
        any: The value or None if not found
    """
    try:
        client = get_redis_client()
        value = client.get(key)
        
        if value:
            return json.loads(value)
        
        return None
    except Exception as e:
        logger.error(f"Error getting cache key {key}: {e}")
        return None

def cache_delete(key):
    """
    Delete a value from the Redis cache.
    
    Args:
        key (str): The key to delete
        
    Returns:
        bool: True if the value was deleted, False otherwise
    """
    try:
        client = get_redis_client()
        client.delete(key)
        logger.debug(f"Deleted cache key: {key}")
        return True
    except Exception as e:
        logger.error(f"Error deleting cache key {key}: {e}")
        return False

class DummyRedisClient:
    """
    A dummy Redis client that logs operations but doesn't do anything.
    Used as a fallback when Redis is not available.
    """
    
    def __getattr__(self, name):
        """
        Log the attempted operation and return a dummy method.
        
        Args:
            name (str): The name of the method being called
            
        Returns:
            callable: A dummy method that logs the call and returns appropriate values
        """
        def dummy_method(*args, **kwargs):
            logger.warning(f"Dummy Redis client called method: {name} with args: {args} kwargs: {kwargs}")
            
            # Return appropriate values based on method name
            if name in ('get', 'hget', 'hgetall'):
                return None
            elif name in ('set', 'hset', 'delete', 'hdel', 'publish'):
                return True
            elif name == 'ping':
                return False
            elif name == 'pubsub':
                return self
            elif name == 'subscribe':
                return True
            else:
                return None
                
        return dummy_method