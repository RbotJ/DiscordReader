"""
Redis Utilities

A collection of Redis-related utilities for working with our Redis cache and pub/sub system.
"""

import logging
import os
import json
import redis
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None

def get_redis_client():
    """
    Get the Redis client singleton.
    
    Returns:
        redis.Redis: Redis client
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            logger.info(f"Connected to Redis at {REDIS_URL}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            # Return a dummy client that logs operations but doesn't fail
            _redis_client = DummyRedisClient()
    
    return _redis_client

def ping_redis():
    """
    Check if Redis is available.
    
    Returns:
        bool: True if Redis is available, False otherwise
    """
    try:
        client = get_redis_client()
        return client.ping()
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return False

def publish_event(channel, data):
    """
    Publish an event to a Redis channel.
    
    Args:
        channel (str): The channel to publish to
        data (dict): The data to publish
        
    Returns:
        bool: True if the event was published, False otherwise
    """
    try:
        client = get_redis_client()
        
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
            
        # Publish the event
        client.publish(channel, json.dumps(data))
        logger.debug(f"Published event to {channel}: {data}")
        return True
    except Exception as e:
        logger.error(f"Error publishing event to {channel}: {e}")
        return False

def subscribe_to_channel(channel, callback):
    """
    Subscribe to a Redis channel.
    
    Args:
        channel (str): The channel to subscribe to
        callback (callable): The callback function to call when a message is received
        
    Returns:
        bool: True if the subscription was created, False otherwise
    """
    try:
        # Create a new connection for the subscription
        pubsub = get_redis_client().pubsub()
        pubsub.subscribe(**{channel: callback})
        logger.info(f"Subscribed to channel: {channel}")
        return True
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