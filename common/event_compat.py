"""
Event System Compatibility Layer

This module provides backward compatibility for event system functionality
during the transition from Redis to PostgreSQL.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from common.db import db
from common.db_models import EventModel
from common.event_constants import *

logger = logging.getLogger(__name__)

# Global event client instance
event_client = None

class EventClient:
    """
    Compatibility client for event system to ensure
    applications can consistently publish and subscribe
    regardless of the underlying implementation.
    """
    
    def __init__(self):
        """Initialize the event client."""
        self.subscribers = {}
        self.initialized = False
        
    def initialize(self):
        """Initialize the event system."""
        try:
            self.initialized = True
            logger.info("Event client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize event client: {e}")
            return False
            
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """
        Publish an event to the specified channel.
        
        Args:
            channel: The channel to publish to
            data: The data to publish
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            event = EventModel()
            event.channel = channel
            event.data = data
            event.created_at = datetime.utcnow()
            
            db.session.add(event)
            db.session.commit()
            
            # Notify any local subscribers
            if channel in self.subscribers:
                for callback in self.subscribers[channel]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}")
            
            logger.debug(f"Published event to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            db.session.rollback()
            return False
    
    def subscribe(self, channel: str, callback=None):
        """
        Subscribe to events on the specified channel.
        
        Args:
            channel: The channel to subscribe to
            callback: Optional callback function to invoke when events are published
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if callback:
                if channel not in self.subscribers:
                    self.subscribers[channel] = []
                    
                if callback not in self.subscribers[channel]:
                    self.subscribers[channel].append(callback)
                    
            logger.debug(f"Subscribed to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to channel: {e}")
            return False
            
    def unsubscribe(self, channel: str, callback=None):
        """
        Unsubscribe from events on the specified channel.
        
        Args:
            channel: The channel to unsubscribe from
            callback: Optional callback function to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if channel in self.subscribers:
                if callback:
                    if callback in self.subscribers[channel]:
                        self.subscribers[channel].remove(callback)
                else:
                    self.subscribers[channel] = []
                    
            logger.debug(f"Unsubscribed from channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel: {e}")
            return False

    def get_latest_events(self, channel: str, since_timestamp: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the latest events for a channel.
        
        Args:
            channel: The channel to get events for
            since_timestamp: Only return events after this timestamp
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        try:
            query = db.session.query(EventModel).filter(
                EventModel.channel == channel
            )
            
            if since_timestamp:
                query = query.filter(EventModel.created_at > since_timestamp)
                
            events = query.order_by(
                EventModel.created_at.desc()
            ).limit(limit).all()
            
            result = []
            for event in events:
                result.append({
                    'id': event.id,
                    'channel': event.channel,
                    'data': event.data,
                    'created_at': event.created_at
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get latest events: {e}")
            return []


def ensure_event_system():
    """
    Ensure the event system is initialized.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global event_client
    
    if event_client is None:
        try:
            event_client = EventClient()
            event_client.initialize()
            logger.info("Event system initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
            return False
            
    return event_client.initialized
    
def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to the specified channel.
    
    Args:
        channel: The channel to publish to
        data: The data to publish
        
    Returns:
        bool: True if successful, False otherwise
    """
    global event_client
    
    if not ensure_event_system():
        logger.error("Event system not ready")
        return False
        
    return event_client.publish(channel, data)
    
def subscribe_to_events(channel: str, callback=None) -> bool:
    """
    Subscribe to events on the specified channel.
    
    Args:
        channel: The channel to subscribe to
        callback: Optional callback function to invoke when events are published
        
    Returns:
        bool: True if successful, False otherwise
    """
    global event_client
    
    if not ensure_event_system():
        logger.error("Event system not ready")
        return False
        
    return event_client.subscribe(channel, callback)
    
def unsubscribe_from_events(channel: str, callback=None) -> bool:
    """
    Unsubscribe from events on the specified channel.
    
    Args:
        channel: The channel to unsubscribe from
        callback: Optional callback function to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    global event_client
    
    if not ensure_event_system():
        logger.error("Event system not ready")
        return False
        
    return event_client.unsubscribe(channel, callback)
    
def get_latest_events(channel: str, since_timestamp: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get the latest events for a channel.
    
    Args:
        channel: The channel to get events for
        since_timestamp: Only return events after this timestamp
        limit: Maximum number of events to return
        
    Returns:
        List of events
    """
    global event_client
    
    if not ensure_event_system():
        logger.error("Event system not ready")
        return []
        
    return event_client.get_latest_events(channel, since_timestamp, limit)