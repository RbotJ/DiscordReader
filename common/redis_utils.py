"""
Redis Utilities Module

This module provides Redis client utilities with fallback implementation
for reliable event handling even when Redis is not available.
"""
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from queue import Queue, Empty
from typing import Any, Dict, List, Set, Optional, Union, Callable, Deque, TypeVar, Generic

import redis
from redis.exceptions import ConnectionError as RedisConnectionError

# Configure logger
logger = logging.getLogger(__name__)

# Redis configuration from environment or defaults
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_URL = os.environ.get("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# Maximum number of messages to store in memory (per channel)
MAX_FALLBACK_MESSAGES = 1000

# Fallback in-memory message store with auto-trimming via deque
# Structure: {channel: deque(messages, maxlen=MAX_FALLBACK_MESSAGES)}
_fallback_messages: Dict[str, Deque[Dict[str, Any]]] = defaultdict(
    lambda: deque(maxlen=MAX_FALLBACK_MESSAGES)
)

# In-memory key-value store for fallback get/set operations
_fallback_kv_store: Dict[str, Any] = {}

# In-memory key expiration data for TTL support
_fallback_expiry: Dict[str, float] = {}

# Subscribers for fallback mode
# Structure: {channel: [callback_functions]}
_fallback_subscribers: Dict[str, List[Callable]] = defaultdict(list)

# Lock for thread-safe operations on fallback structures
_fallback_lock = threading.Lock()

# Connection pool for Redis (module-level singleton)
try:
    _redis_pool = redis.ConnectionPool.from_url(REDIS_URL)
    logger.debug("Redis connection pool initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Redis connection pool: {e}")
    _redis_pool = None

# Type variable for Redis client interface
T = TypeVar('T')

class FallbackPubSub:
    """
    Fallback implementation of Redis PubSub functionality for when
    Redis is not available. Implements a compatible interface.
    """
    
    def __init__(self, channels: List[str]):
        """
        Initialize the fallback PubSub.
        
        Args:
            channels: List of channels to subscribe to
        """
        self.channels = set(channels)
        self.running = True
        
        # Message queue for this subscriber using thread-safe Queue
        self.message_queue: Queue = Queue()
        
        # Register with the fallback system
        with _fallback_lock:
            for channel in self.channels:
                if self._message_callback not in _fallback_subscribers[channel]:
                    _fallback_subscribers[channel].append(self._message_callback)
    
    def _message_callback(self, message: Dict[str, Any]) -> None:
        """
        Callback for receiving messages from the fallback system.
        
        Args:
            message: Message dictionary
        """
        if not self.running:
            return
            
        # Queue.put is thread-safe, no need for explicit locks
        self.message_queue.put(message)
    
    def get_message(self, timeout: float = 0.01) -> Optional[Dict[str, Any]]:
        """
        Get a message from the queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Message dictionary or None if no message
        """
        try:
            # Use the timeout parameter with Queue.get
            return self.message_queue.get(block=True, timeout=timeout)
        except Empty:
            return None
    
    def subscribe(self, *channels) -> None:
        """
        Subscribe to additional channels.
        
        Args:
            *channels: Channel names to subscribe to
        """
        with _fallback_lock:
            for channel in channels:
                self.channels.add(channel)
                if self._message_callback not in _fallback_subscribers[channel]:
                    _fallback_subscribers[channel].append(self._message_callback)
    
    def unsubscribe(self, *args) -> None:
        """
        Unsubscribe from channels.
        
        Args:
            *args: Channel names to unsubscribe from, or all if none provided
        """
        channels_to_unsub = set(args) if args else self.channels.copy()
        
        with _fallback_lock:
            for channel in channels_to_unsub:
                if channel in self.channels:
                    self.channels.remove(channel)
                    
                if channel in _fallback_subscribers:
                    if self._message_callback in _fallback_subscribers[channel]:
                        _fallback_subscribers[channel].remove(self._message_callback)
        
        self.running = len(self.channels) > 0
        
    def close(self) -> None:
        """
        Close the subscription and clean up resources.
        """
        self.unsubscribe()
        self.running = False
        
    def run_in_thread(self, sleep_time: float = 0.1) -> threading.Thread:
        """
        Run the PubSub listener in a background thread.
        
        Args:
            sleep_time: Sleep time between checking for messages
            
        Returns:
            Thread object
        """
        def listener_thread():
            while getattr(thread, "running", True):
                message = self.get_message(timeout=sleep_time)
                if message:
                    # Process message if a callback was provided
                    if hasattr(thread, "callback") and thread.callback:
                        try:
                            thread.callback(message)
                        except Exception as e:
                            logger.error(f"Error in pubsub callback: {e}")
                time.sleep(0.001)  # Tiny sleep to prevent CPU hogging
            
            # Clean up when thread is stopped
            self.close()
        
        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.running = True
        thread.callback = None
        thread.stop = lambda: setattr(thread, "running", False)
        thread.start()
        
        return thread


class InMemoryRedisClient:
    """
    In-memory implementation of Redis client interface.
    Used as a fallback when Redis is not available.
    """
    
    def __init__(self):
        """Initialize the in-memory Redis client."""
        self.pubsub_threads = []
    
    def get(self, key: str) -> Optional[str]:
        """
        Get a value from the in-memory store.
        
        Args:
            key: Key to retrieve
            
        Returns:
            Value or None if not found or expired
        """
        with _fallback_lock:
            # Check if key exists and is not expired
            if key in _fallback_kv_store:
                # Check expiration
                if key in _fallback_expiry and time.time() > _fallback_expiry[key]:
                    # Key has expired
                    del _fallback_kv_store[key]
                    del _fallback_expiry[key]
                    return None
                
                value = _fallback_kv_store[key]
                # Convert to string if needed to match Redis behavior
                return str(value) if value is not None else None
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set a value in the in-memory store.
        
        Args:
            key: Key to set
            value: Value to store
            ex: Expiration time in seconds
            
        Returns:
            True if successful
        """
        with _fallback_lock:
            _fallback_kv_store[key] = value
            
            # Set expiration if provided
            if ex is not None:
                _fallback_expiry[key] = time.time() + ex
                
        return True
        
    def delete(self, key: str) -> bool:
        """
        Delete a key from the in-memory store.
        
        Args:
            key: Key to delete
            
        Returns:
            True if deleted, False if key not found
        """
        with _fallback_lock:
            if key in _fallback_kv_store:
                del _fallback_kv_store[key]
                if key in _fallback_expiry:
                    del _fallback_expiry[key]
                return True
            return False
    
    def publish(self, channel: str, data: Union[Dict[str, Any], str]) -> bool:
        """
        Publish a message to a channel in the in-memory messaging system.
        
        Args:
            channel: Channel name
            data: Message data
            
        Returns:
            True if successful
        """
        # Convert data to JSON string if it's a dictionary
        if isinstance(data, dict):
            try:
                message_data = json.dumps(data)
            except Exception as e:
                logger.error(f"Error serializing message data: {e}")
                return False
        else:
            message_data = data
            
        # Create message structure
        message = {
            "type": "message",
            "pattern": None,
            "channel": channel,
            "data": message_data
        }
        
        # Add to fallback messages queue
        with _fallback_lock:
            _fallback_messages[channel].append(message)
            
            # Notify subscribers
            for callback in _fallback_subscribers[channel]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
        
        return True
    
    def pubsub(self) -> FallbackPubSub:
        """
        Get a pubsub object for the in-memory messaging system.
        
        Returns:
            FallbackPubSub instance
        """
        return FallbackPubSub([])
    
    def subscribe(self, *channels) -> FallbackPubSub:
        """
        Subscribe to channels.
        
        Args:
            *channels: Channel names
            
        Returns:
            FallbackPubSub instance
        """
        pubsub = FallbackPubSub(channels)
        return pubsub

class RedisClient:
    """
    Redis client wrapper with fallback implementation for when
    Redis is not available.
    """
    
    def __init__(self, url: str = REDIS_URL, max_retries: int = 3):
        """
        Initialize the Redis client.
        
        Args:
            url: Redis URL (default: redis://127.0.0.1:6379/0)
            max_retries: Maximum number of retries for connecting to Redis
        """
        self.url = url
        self.client = None
        self.fallback_mode = False
        
        # Try to connect to Redis using the shared connection pool
        self._connect(max_retries)
    
    def _connect(self, max_retries: int = 3) -> None:
        """
        Connect to Redis with retries using the shared connection pool.
        
        Args:
            max_retries: Maximum number of retries
        """
        retries = 0
        
        while retries < max_retries:
            try:
                # Use the shared connection pool if available
                if _redis_pool is not None:
                    self.client = redis.Redis(connection_pool=_redis_pool)
                else:
                    self.client = redis.from_url(self.url)
                    
                # Test connection
                self.client.ping()
                self.fallback_mode = False
                return
            except redis.exceptions.ConnectionError:
                retries += 1
                
                # No Redis startup attempts, just retry with backoff
                time.sleep(0.5 * retries)
        
        # If we get here, we couldn't connect after max_retries
        self.client = None
        self.fallback_mode = True
        logger.warning(f"Could not connect to Redis at {self.url}. Using fallback mode")
    
    def publish(self, channel: str, data: Union[Dict[str, Any], str]) -> bool:
        """
        Publish a message to a channel.
        
        Args:
            channel: Channel name
            data: Message data (dictionary or string)
            
        Returns:
            bool: Success status
        """
        # Ensure data is serializable
        if isinstance(data, dict):
            try:
                message_str = json.dumps(data)
            except (TypeError, ValueError) as e:
                logger.error(f"Error serializing message: {e}")
                return False
        else:
            message_str = str(data)
        
        if not self.fallback_mode and self.client:
            try:
                return bool(self.client.publish(channel, message_str))
            except Exception as e:
                logger.error(f"Error publishing to Redis: {e}")
                # Switch to fallback mode on error
                self.fallback_mode = True
        
        # Fallback mode
        try:
            # Parse message string to dictionary if possible
            try:
                message_data = json.loads(message_str)
            except json.JSONDecodeError:
                message_data = {"data": message_str}
            
            # Create standard message format
            message = {
                "type": "message",
                "channel": channel,
                "data": message_data
            }
            
            with _fallback_lock:
                # Add to message store
                _fallback_messages[channel].append(message_data)
                
                # Trim message store if needed
                if len(_fallback_messages[channel]) > MAX_FALLBACK_MESSAGES:
                    _fallback_messages[channel] = _fallback_messages[channel][-MAX_FALLBACK_MESSAGES:]
                
                # Notify subscribers
                for callback in _fallback_subscribers.get(channel, []):
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Error in fallback subscriber callback: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error in fallback publish: {e}")
            return False
    
    def subscribe(self, *channels) -> Union[redis.client.PubSub, FallbackPubSub]:
        """
        Subscribe to one or more channels.
        
        Args:
            *channels: Channel names to subscribe to
            
        Returns:
            PubSub object
        """
        if not self.fallback_mode and self.client:
            try:
                pubsub = self.client.pubsub()
                pubsub.subscribe(*channels)
                return pubsub
            except Exception as e:
                logger.error(f"Error subscribing to Redis channels: {e}")
                # Switch to fallback mode on error
                self.fallback_mode = True
        
        # Fallback mode
        return FallbackPubSub(list(channels))
    
    def get(self, key: str) -> Optional[str]:
        """
        Get a value from Redis.
        
        Args:
            key: Key to get
            
        Returns:
            Value or None if not found
        """
        if not self.fallback_mode and self.client:
            try:
                value = self.client.get(key)
                if value is not None and isinstance(value, bytes):
                    return value.decode('utf-8')
                return value
            except Exception as e:
                logger.error(f"Error getting value from Redis: {e}")
                # Switch to fallback mode on error
                self.fallback_mode = True
        
        # Use fallback key-value store
        with _fallback_lock:
            # Check if key exists and is not expired
            if key in _fallback_kv_store:
                # Check expiration
                if key in _fallback_expiry and time.time() > _fallback_expiry[key]:
                    # Key has expired
                    del _fallback_kv_store[key]
                    del _fallback_expiry[key]
                    return None
                
                return str(_fallback_kv_store[key])
        return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: Key to set
            value: Value to set
            ex: Expiration time in seconds
            
        Returns:
            bool: Success status
        """
        if not self.fallback_mode and self.client:
            try:
                self.client.set(key, value, ex=ex)
                return True
            except Exception as e:
                logger.error(f"Error setting value in Redis: {e}")
                # Switch to fallback mode on error
                self.fallback_mode = True
        
        # Use fallback key-value store
        with _fallback_lock:
            _fallback_kv_store[key] = value
            
            # Set expiration if provided
            if ex is not None:
                _fallback_expiry[key] = time.time() + ex
                
        return True

def ensure_redis_is_running() -> bool:
    """
    Ensure the Redis server is running.
    
    Returns:
        bool: True if Redis server is running, False otherwise
    """
    try:
        # Try to connect to Redis
        client = redis.from_url(REDIS_URL)
        # Test connection
        client.ping()
        return True
    except Exception:
        # Instead of trying to start Redis, just return False
        # This avoids timeouts and speeds up startup
        logger.warning("Redis server not running and will not be started automatically")
        return False

def get_redis_client() -> RedisClient:
    """
    Get a Redis client instance.
    
    Returns:
        RedisClient: Redis client instance
    """
    return RedisClient()

def publish_event(channel: str, event_type: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to a Redis channel.
    
    Args:
        channel: Redis channel to publish to
        event_type: Event type identifier
        data: Event data
        
    Returns:
        bool: Success status
    """
    try:
        # Create event payload
        payload = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        # Get Redis client and publish - use a global client to avoid startup attempts
        if not hasattr(publish_event, '_redis_client'):
            logger.info("Initializing Redis client for event publishing")
            publish_event._redis_client = RedisClient()
            
        return publish_event._redis_client.publish(channel, payload)
    except Exception as e:
        logger.error(f"Error publishing event to {channel}: {e}")
        return False