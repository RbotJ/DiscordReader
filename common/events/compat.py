"""
Event System Compatibility Module

This module provides backward compatibility for the event system transition
from Redis to PostgreSQL. It ensures existing code continues to work while
we migrate to the new event system architecture.
"""
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Create a simple client for compatibility
class EventClient:
    """Simple client for the event system."""
    def __init__(self):
        self.connected = False
    
    def connect(self):
        """Connect to event system."""
        self.connected = True
        return True
    
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """Publish an event to the specified channel."""
        from common.events import publish_event
        return publish_event(channel, data)
    
    def subscribe(self, channel: str, callback):
        """Subscribe to events on the specified channel."""
        from common.events import subscribe_to_events
        return subscribe_to_events(channel, callback)

# Create a singleton instance
event_client = EventClient()

def ensure_event_system() -> bool:
    """
    Ensure the event system is initialized.
    
    Returns:
        bool: True if the event system is ready, False otherwise
    """
    try:
        # Connect the client
        if not event_client.connected:
            event_client.connect()
            
        # Initialize the event system
        from common.events import initialize_events
        return initialize_events()
    except Exception as e:
        logger.error(f"Failed to ensure event system: {e}")
        return False