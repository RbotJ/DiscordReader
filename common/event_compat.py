
"""
Event System Compatibility Layer

Maps legacy event operations to PostgreSQL event system calls.
"""
import logging
from typing import Any, Optional, Dict
from common.events import (
    publish_event, 
    subscribe_to_events,
    cache_data,
    get_from_cache,
    delete_from_cache
)

logger = logging.getLogger(__name__)

class EventClient:
    """Compatibility class that maps legacy operations to PostgreSQL"""
    
    @staticmethod
    def publish(channel: str, data: Dict[str, Any]) -> bool:
        """Publish event to channel"""
        return publish_event(channel, data)
    
    @staticmethod
    def subscribe(channel: str) -> bool:
        """Subscribe to channel"""
        return subscribe_to_events(channel)
    
    @staticmethod
    def set(key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set cache value"""
        return cache_data(key, value, ex or 900)
    
    @staticmethod
    def get(key: str) -> Any:
        """Get cache value"""
        return get_from_cache(key)
    
    @staticmethod
    def delete(key: str) -> bool:
        """Delete cache value"""
        return delete_from_cache(key)

# Create global instance for compatibility 
event_client = EventClient()

def ensure_event_system() -> bool:
    """Check if event system is running"""
    try:
        from common.events import get_status
        status = get_status()
        return status.get('running', False)
    except Exception as e:
        logger.error(f"Error checking event system status: {e}")
        return False

def init_event_client() -> bool:
    """Initialize the event system compatibility layer"""
    logger.info("Event system compatibility layer initialized (using PostgreSQL)")
    return True

def ping_event_system() -> bool:
    """Check if the event system is accessible"""
    return ensure_event_system()
