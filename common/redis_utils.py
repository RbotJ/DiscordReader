import json
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional, Union, TypeVar, cast, Awaitable
import redis
from datetime import datetime, date

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for return values
T = TypeVar('T')
ResponseT = Union[bytes, str, int, float, List[Any], Dict[str, Any], bool, None]

# Global redis client instance
redis_client = None

def ensure_redis_is_running() -> bool:
    """Ensure Redis server is running, attempt to start it if not."""
    try:
        # Try to check if Redis is already running
        client = redis.Redis(host='127.0.0.1', port=6379)
        client.ping()
        logger.info("Redis server is already running")
        return True
    except (redis.ConnectionError, redis.RedisError):
        logger.info("Redis not running, attempting to start it...")
        
        try:
            # Attempt to kill any existing Redis processes
            subprocess.run(['pkill', '-f', 'redis-server'], 
                          stderr=subprocess.DEVNULL, 
                          check=False)
            
            # Start Redis server with suitable configuration
            subprocess.Popen(
                ['redis-server', '--daemonize', 'yes', '--protected-mode', 'no', 
                 '--maxmemory', '100mb', '--maxmemory-policy', 'allkeys-lru'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for Redis to start
            for i in range(10):
                time.sleep(0.5)
                try:
                    client = redis.Redis(host='127.0.0.1', port=6379)
                    client.ping()
                    logger.info("Successfully started Redis server")
                    return True
                except (redis.ConnectionError, redis.RedisError):
                    pass
            
            logger.error("Failed to start Redis server after multiple attempts")
            return False
        except Exception as e:
            logger.error(f"Error starting Redis server: {e}")
            return False

# Custom JSON encoder for serializing datetime and date objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)


class MockPubSub:
    """Mock implementation of Redis PubSub for fallback when Redis is unavailable."""
    def __init__(self):
        self.channels = []
        
    def subscribe(self, *channels):
        """Mock subscribe to channels."""
        self.channels.extend(channels)
        
    def get_message(self, timeout=None):
        """Mock get_message that returns None."""
        return None

class RedisClient:
    def __init__(self, redis_url: str = "redis://127.0.0.1:6379/0"):
        """Initialize Redis client with the given URL."""
        self.redis_url = redis_url
        self.available = False
        
        # Try to ensure Redis is running before connecting
        try:
            self._attempt_to_start_redis()
        except Exception as e:
            logger.warning(f"Failed to start Redis server: {e}")
        
        # Now try to connect
        try:
            self.redis = redis.from_url(redis_url)
            # Test the connection
            self.redis.ping()
            self.available = True
            logger.info(f"Redis client initialized with URL: {redis_url}")
        except (redis.ConnectionError, redis.RedisError) as e:
            logger.warning(f"Could not connect to Redis at {redis_url}. Using fallback mode: {e}")
            self.redis = None
    
    def _attempt_to_start_redis(self):
        """Attempt to start Redis server if not already running."""
        ensure_redis_is_running()
        
    def publish(self, channel: str, message: Union[str, Dict, List]) -> int:
        """Publish a message to a Redis channel."""
        if not isinstance(message, str):
            message = json.dumps(message, cls=DateTimeEncoder)
        
        if not self.available:
            logger.debug(f"Redis unavailable, skipping publish to channel {channel}")
            return 0
            
        try:
            if self.redis is None:
                logger.debug(f"Redis client is None, skipping publish to channel {channel}")
                return 0
                
            result = self.redis.publish(channel, message)
            logger.debug(f"Published message to channel {channel}")
            return int(result) if result is not None else 0
        except Exception as e:
            logger.error(f"Error publishing to channel {channel}: {e}")
            return 0
    
    def subscribe(self, channels: Union[str, List[str]]):
        """Subscribe to one or more Redis channels."""
        if isinstance(channels, str):
            channels = [channels]
        
        if not self.available or self.redis is None:
            logger.debug(f"Redis unavailable, returning mock PubSub for channels: {channels}")
            mock_pubsub = MockPubSub()
            mock_pubsub.subscribe(*channels)
            return mock_pubsub
        
        try:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(*channels)
            logger.debug(f"Subscribed to channels: {channels}")
            return pubsub
        except Exception as e:
            logger.error(f"Error subscribing to channels {channels}: {e}")
            mock_pubsub = MockPubSub()
            mock_pubsub.subscribe(*channels)
            return mock_pubsub
    
    def set(self, key: str, value: Union[str, Dict, List], expiration: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis with optional expiration in seconds."""
        if not isinstance(value, str):
            value = json.dumps(value, cls=DateTimeEncoder)
        
        if not self.available or self.redis is None:
            logger.debug(f"Redis unavailable, skipping set key {key}")
            return False
        
        try:
            result = self.redis.set(key, value, ex=expiration)
            logger.debug(f"Set key {key} in Redis")
            return bool(result) if result is not None else False
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            return False
    
    def get(self, key: str, as_json: bool = False) -> Any:
        """Get a value from Redis by key, optionally parsing as JSON."""
        if not self.available or self.redis is None:
            logger.debug(f"Redis unavailable, returning None for key {key}")
            return None
        
        try:
            value = self.redis.get(key)
            
            if value is None:
                return None
            
            # Handle both Redis values and async Redis values
            if isinstance(value, bytes):
                value_str = value.decode('utf-8')
            elif hasattr(value, 'decode'):
                value_str = value.decode('utf-8')
            else:
                # Handle potential non-string values returned by some Redis clients
                logger.warning(f"Unexpected Redis value type: {type(value)}")
                value_str = str(value)
            
            if as_json:
                try:
                    return json.loads(value_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Redis value as JSON: {value_str}")
                    return value_str
            
            return value_str
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None
    
    def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        if not self.available or self.redis is None:
            logger.debug(f"Redis unavailable, skipping delete key {key}")
            return 0
        
        try:
            result = self.redis.delete(key)
            logger.debug(f"Deleted key {key} from Redis")
            return int(result) if result is not None else 0
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return 0
    
    def list_push(self, key: str, value: Union[str, Dict, List]) -> int:
        """Push a value to a Redis list."""
        if not isinstance(value, str):
            value = json.dumps(value, cls=DateTimeEncoder)
        
        if not self.available or self.redis is None:
            logger.debug(f"Redis unavailable, skipping push to list {key}")
            return 0
        
        try:
            result = self.redis.rpush(key, value)
            logger.debug(f"Pushed value to list {key} in Redis")
            return int(result) if result is not None else 0
        except Exception as e:
            logger.error(f"Error pushing to list {key} in Redis: {e}")
            return 0
    
    def list_get_all(self, key: str, as_json: bool = False) -> List:
        """Get all values from a Redis list, optionally parsing as JSON."""
        if not self.available or self.redis is None:
            logger.debug(f"Redis unavailable, returning empty list for key {key}")
            return []
        
        try:
            values = self.redis.lrange(key, 0, -1)
            
            # Handle the case where values might be an awaitable
            if hasattr(values, '__await__'):
                logger.warning(f"Received awaitable for lrange on key {key}, returning empty list")
                return []
                
            if not values:
                return []
                
            if as_json:
                result = []
                for value in values:
                    if value is None:
                        continue
                        
                    try:
                        # Handle both bytes and string values
                        if isinstance(value, bytes):
                            decoded_value = value.decode('utf-8')
                        elif hasattr(value, 'decode'):
                            decoded_value = value.decode('utf-8')
                        else:
                            decoded_value = str(value)
                            
                        result.append(json.loads(decoded_value))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse Redis list value as JSON: {value}")
                        if isinstance(value, bytes):
                            result.append(value.decode('utf-8'))
                        elif hasattr(value, 'decode'):
                            result.append(value.decode('utf-8'))
                        else:
                            result.append(str(value))
                return result
            
            # Handle both bytes and string values for non-JSON return
            result = []
            for value in values:
                if value is None:
                    continue
                    
                if isinstance(value, bytes):
                    result.append(value.decode('utf-8'))
                elif hasattr(value, 'decode'):
                    result.append(value.decode('utf-8'))
                else:
                    result.append(str(value))
            return result
            
        except Exception as e:
            logger.error(f"Error getting list {key} from Redis: {e}")
            return []
