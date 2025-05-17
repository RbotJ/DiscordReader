"""
Redis Utilities Module

This module provides Redis client utilities with fallback implementation
for reliable event handling even when Redis is not available.
"""
import json
import logging
import subprocess
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Set, Optional, Union, Callable

import redis
from redis.exceptions import ConnectionError as RedisConnectionError

# Configure logger
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Maximum number of messages to store in memory (per channel)
MAX_FALLBACK_MESSAGES = 1000

# Fallback in-memory message store
# Structure: {channel: [messages]}
_fallback_messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

# Subscribers for fallback mode
# Structure: {channel: [callback_functions]}
_fallback_subscribers: Dict[str, List[Callable]] = defaultdict(list)

# Lock for thread-safe operations on fallback structures
_fallback_lock = threading.Lock()

def _start_redis_server() -> bool:
    """
    Attempt to start the Redis server if it's not running.
    
    Returns:
        bool: True if Redis server started successfully, False otherwise
    """
    try:
        # Try to start Redis server using the script
        result = subprocess.run(
            ["bash", "./start_redis.sh"],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        
        if result.returncode == 0:
            logger.info("Redis server started successfully")
            # Give it a moment to initialize
            time.sleep(1)
            return True
        else:
            logger.error(f"Failed to start Redis server: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error starting Redis server: {e}")
        return False

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
        
        # Register with the fallback system
        with _fallback_lock:
            for channel in self.channels:
                if self._message_callback not in _fallback_subscribers[channel]:
                    _fallback_subscribers[channel].append(self._message_callback)
        
        # Message queue for this subscriber
        self.message_queue: List[Dict[str, Any]] = []
        
        # Lock for thread-safe operations on the message queue
        self.queue_lock = threading.Lock()
    
    def _message_callback(self, message: Dict[str, Any]) -> None:
        """
        Callback for receiving messages from the fallback system.
        
        Args:
            message: Message dictionary
        """
        if not self.running:
            return
            
        with self.queue_lock:
            self.message_queue.append(message)
    
    def get_message(self, timeout: float = 0.01) -> Optional[Dict[str, Any]]:
        """
        Get a message from the queue.
        
        Args:
            timeout: Timeout in seconds (used for API compatibility)
            
        Returns:
            Message dictionary or None if no message
        """
        # timeout is ignored in fallback mode since we just check the queue
        with self.queue_lock:
            if self.message_queue:
                return self.message_queue.pop(0)
            return None
    
    def unsubscribe(self, *args) -> None:
        """
        Unsubscribe from channels.
        
        Args:
            *args: Channel names to unsubscribe from, or all if none provided
        """
        channels_to_unsub = set(args) if args else self.channels
        
        with _fallback_lock:
            for channel in channels_to_unsub:
                if channel in self.channels:
                    self.channels.remove(channel)
                    
                if channel in _fallback_subscribers:
                    if self._message_callback in _fallback_subscribers[channel]:
                        _fallback_subscribers[channel].remove(self._message_callback)
        
        self.running = len(self.channels) > 0

class RedisClient:
    """
    Redis client wrapper with fallback implementation for when
    Redis is not available.
    """
    
    def __init__(self, url: str = REDIS_URL, max_retries: int = 5):
        """
        Initialize the Redis client.
        
        Args:
            url: Redis URL (default: redis://127.0.0.1:6379/0)
            max_retries: Maximum number of retries for connecting to Redis
        """
        self.url = url
        self.client = None
        self.fallback_mode = False
        
        # Try to connect to Redis
        self._connect(max_retries)
    
    def _connect(self, max_retries: int = 5) -> None:
        """
        Connect to Redis with retries.
        
        Args:
            max_retries: Maximum number of retries
        """
        retries = 0
        
        while retries < max_retries:
            try:
                self.client = redis.from_url(self.url)
                # Test connection
                self.client.ping()
                self.fallback_mode = False
                return
            except redis.exceptions.ConnectionError:
                retries += 1
                
                if retries == 1:
                    # On first failure, try to start Redis server
                    logger.info("Redis not running, attempting to start it...")
                    if _start_redis_server():
                        # Retry immediately if server started
                        continue
                
                time.sleep(1)
        
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
                return self.client.get(key)
            except Exception as e:
                logger.error(f"Error getting value from Redis: {e}")
                # Switch to fallback mode on error
                self.fallback_mode = True
        
        # No fallback for get operation
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
        
        # No fallback for set operation
        return False

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
        # Redis is not running, try to start it
        return _start_redis_server()