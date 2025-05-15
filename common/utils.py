import os
import json
import logging
import redis
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global Redis connection
redis_client = None

def setup_redis_connection() -> redis.Redis:
    """Initialize Redis connection for pub/sub communication"""
    global redis_client
    try:
        # Use the REDIS_URL environment variable or default to localhost
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        logger.info(f"Connected to Redis at {redis_url}")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        # Fall back to a dummy implementation for development
        return DummyRedis()

def get_redis_client() -> redis.Redis:
    """Get the Redis client, initialize if needed"""
    global redis_client
    if redis_client is None:
        redis_client = setup_redis_connection()
    return redis_client

def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """Publish an event to Redis pub/sub"""
    try:
        client = get_redis_client()
        # Add timestamp to all events
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        message = json.dumps(data)
        client.publish(channel, message)
        logger.debug(f"Published to {channel}: {message}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish to {channel}: {str(e)}")
        return False

def subscribe_to_channel(channel: str, callback) -> None:
    """Subscribe to a Redis channel and process messages"""
    try:
        client = get_redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe(channel)
        
        logger.info(f"Subscribed to channel: {channel}")
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    callback(data)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
    except Exception as e:
        logger.error(f"Subscription error for {channel}: {str(e)}")

def load_config() -> Dict[str, Any]:
    """Load application configuration"""
    config = {
        "alpaca": {
            "api_key": os.environ.get("ALPACA_API_KEY", ""),
            "api_secret": os.environ.get("ALPACA_API_SECRET", ""),
            "base_url": os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            "data_url": os.environ.get("ALPACA_DATA_URL", "https://data.alpaca.markets"),
        },
        "settings": {
            "max_positions": int(os.environ.get("MAX_POSITIONS", "5")),
            "max_position_size": float(os.environ.get("MAX_POSITION_SIZE", "0.1")),  # Fraction of account
            "risk_per_trade": float(os.environ.get("RISK_PER_TRADE", "0.01")),  # 1% account risk per trade
            "default_option_days": int(os.environ.get("DEFAULT_OPTION_DAYS", "30")),
            "target_delta": float(os.environ.get("TARGET_DELTA", "0.3")),
            "notification_webhook": os.environ.get("NOTIFICATION_WEBHOOK", ""),
        }
    }
    return config

class DummyRedis:
    """Dummy Redis implementation for development without Redis server"""
    def __init__(self):
        self.data = {}
        self.pubsub_messages = {}
        logger.warning("Using dummy Redis implementation - for development only!")
    
    def publish(self, channel, message):
        """Simulate Redis publish"""
        if channel not in self.pubsub_messages:
            self.pubsub_messages[channel] = []
        self.pubsub_messages[channel].append(message)
        logger.debug(f"[DUMMY] Published to {channel}: {message}")
        return 1
    
    def subscribe(self, channel):
        """Simulate Redis subscribe"""
        logger.debug(f"[DUMMY] Subscribed to {channel}")
        return True
    
    def pubsub(self):
        """Return a dummy pubsub object"""
        return DummyPubSub(self)
    
    def get(self, key):
        """Simulate Redis get"""
        return self.data.get(key)
    
    def set(self, key, value):
        """Simulate Redis set"""
        self.data[key] = value
        return True
    
    def delete(self, key):
        """Simulate Redis delete"""
        if key in self.data:
            del self.data[key]
        return True
    
    def from_url(self, url):
        """Simulate Redis from_url"""
        return self

class DummyPubSub:
    """Dummy PubSub implementation"""
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.subscribed_channels = []
    
    def subscribe(self, channel):
        """Simulate subscribe"""
        self.subscribed_channels.append(channel)
    
    def listen(self):
        """Simulate listen - yields nothing in dummy implementation"""
        # In a real implementation, this would yield messages
        # For the dummy version, we'll just sleep to avoid consuming CPU
        import time
        while True:
            time.sleep(60)
