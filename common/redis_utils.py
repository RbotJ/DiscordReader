import json
import logging
from typing import Any, Dict, List, Optional, Union
import redis
from datetime import datetime, date

# Configure logging
logger = logging.getLogger(__name__)

# Custom JSON encoder for serializing datetime and date objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class RedisClient:
    def __init__(self, redis_url: str = "redis://127.0.0.1:6379/0"):
        """Initialize Redis client with the given URL."""
        self.redis = redis.from_url(redis_url)
        logger.info(f"Redis client initialized with URL: {redis_url}")
        
    def publish(self, channel: str, message: Union[str, Dict, List]) -> int:
        """Publish a message to a Redis channel."""
        if not isinstance(message, str):
            message = json.dumps(message, cls=DateTimeEncoder)
        
        try:
            result = self.redis.publish(channel, message)
            logger.debug(f"Published message to channel {channel}")
            return result
        except Exception as e:
            logger.error(f"Error publishing to channel {channel}: {e}")
            raise
    
    def subscribe(self, channels: Union[str, List[str]]):
        """Subscribe to one or more Redis channels."""
        if isinstance(channels, str):
            channels = [channels]
        
        try:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(*channels)
            logger.debug(f"Subscribed to channels: {channels}")
            return pubsub
        except Exception as e:
            logger.error(f"Error subscribing to channels {channels}: {e}")
            raise
    
    def set(self, key: str, value: Union[str, Dict, List], expiration: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis with optional expiration in seconds."""
        if not isinstance(value, str):
            value = json.dumps(value, cls=DateTimeEncoder)
        
        try:
            result = self.redis.set(key, value, ex=expiration)
            logger.debug(f"Set key {key} in Redis")
            return result
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            raise
    
    def get(self, key: str, as_json: bool = False) -> Any:
        """Get a value from Redis by key, optionally parsing as JSON."""
        try:
            value = self.redis.get(key)
            
            if value is None:
                return None
            
            value_str = value.decode('utf-8')
            
            if as_json:
                try:
                    return json.loads(value_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Redis value as JSON: {value_str}")
                    return value_str
            
            return value_str
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            raise
    
    def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        try:
            result = self.redis.delete(key)
            logger.debug(f"Deleted key {key} from Redis")
            return result
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            raise
    
    def list_push(self, key: str, value: Union[str, Dict, List]) -> int:
        """Push a value to a Redis list."""
        if not isinstance(value, str):
            value = json.dumps(value, cls=DateTimeEncoder)
        
        try:
            result = self.redis.rpush(key, value)
            logger.debug(f"Pushed value to list {key} in Redis")
            return result
        except Exception as e:
            logger.error(f"Error pushing to list {key} in Redis: {e}")
            raise
    
    def list_get_all(self, key: str, as_json: bool = False) -> List:
        """Get all values from a Redis list, optionally parsing as JSON."""
        try:
            values = self.redis.lrange(key, 0, -1)
            
            if as_json:
                result = []
                for value in values:
                    try:
                        result.append(json.loads(value.decode('utf-8')))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse Redis list value as JSON: {value}")
                        result.append(value.decode('utf-8'))
                return result
            
            return [value.decode('utf-8') for value in values]
        except Exception as e:
            logger.error(f"Error getting list {key} from Redis: {e}")
            raise
