"""
Event System Compatibility Module

This module provides backward compatibility for the event system transition
from Redis to PostgreSQL. It ensures existing code continues to work while
we migrate to the new event system architecture.
"""
import logging
from typing import Dict, Any, Optional, Callable
import json
import time
from datetime import datetime

from common.db import db
from common.db_models import EventModel

logger = logging.getLogger(__name__)

class EventClient:
    """Simple client for the event system."""
    def __init__(self):
        """Initialize event client."""
        self.connected = False
        self.callbacks = {}
        
    def connect(self):
        """Connect to event system."""
        try:
            self.connected = True
            logger.info("EventClient connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect EventClient: {e}")
            self.connected = False
            return False
            
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """Publish an event to the specified channel."""
        try:
            if not self.connected:
                self.connect()
                
            # Create event manually to avoid constructor issues
            event = EventModel()
            event.channel = channel
            event.data = data
            event.created_at = datetime.utcnow()
            
            db.session.add(event)
            db.session.commit()
            
            logger.debug(f"Published event to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            db.session.rollback()
            return False
            
    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to events on the specified channel."""
        try:
            if channel not in self.callbacks:
                self.callbacks[channel] = []
            
            self.callbacks[channel].append(callback)
            logger.info(f"Subscribed to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            return False

def ensure_event_system() -> bool:
    """
    Ensure the event system is initialized.
    
    Returns:
        bool: True if the event system is ready, False otherwise
    """
    try:
        # Check if the events table exists
        event_count = db.session.query(EventModel).count()
        logger.info(f"Event system ready with {event_count} stored events")
        return True
    except Exception as e:
        logger.error(f"Event system not ready: {e}")
        return False

def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to the specified channel.
    
    Args:
        channel: The channel to publish to
        data: The data to publish
        
    Returns:
        bool: True if successful, False otherwise
    """
    client = EventClient()
    return client.publish(channel, data)

def get_latest_events(channel: str, limit: int = 10) -> list:
    """
    Get the latest events from the specified channel.
    
    Args:
        channel: The channel to get events from
        limit: Maximum number of events to retrieve
        
    Returns:
        list: List of events, newest first
    """
    try:
        events = db.session.query(EventModel).filter(
            EventModel.channel == channel
        ).order_by(
            EventModel.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for event in events:
            result.append({
                'id': event.id,
                'channel': event.channel,
                'data': event.data,
                'created_at': event.created_at.isoformat() if event.created_at else None
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get latest events: {e}")
        return []
        
# Export event_client for backward compatibility with existing code
event_client = EventClient()