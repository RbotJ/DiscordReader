"""
Event System Module

This module provides a centralized event system for the trading application.
It handles publishing and subscribing to events using the PostgreSQL database
as the event bus.
"""
import logging
import json
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime

from common.db import db
from common.db_models import EventModel
from common.events.constants import EventChannels

logger = logging.getLogger(__name__)

# Function for initializing the event system - called from main.py
def initialize_events():
    """
    Initialize the event system.
    
    This function should be called once at application startup.
    """
    try:
        EventSystem.initialize()
        logger.info("Event system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize event system: {e}")
        return False

class EventSystem:
    """
    Event system for handling application-wide events.
    
    This class provides methods for publishing and subscribing to events
    using the database as the event bus.
    """
    
    _subscribers = {}
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize the event system."""
        if cls._initialized:
            return
            
        try:
            # Create event listener
            cls._initialized = True
            logger.info("Event system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
    
    @classmethod
    def publish(cls, channel: str, data: Dict[str, Any]) -> bool:
        """
        Publish an event to the specified channel.
        
        Args:
            channel: Event channel name
            data: Event data to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create event record
            event = EventModel(
                channel=channel,
                data=data
            )
            
            # Store in database
            db.session.add(event)
            db.session.commit()
            
            logger.info(f"Published event to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            db.session.rollback()
            return False
    
    @classmethod
    def subscribe(cls, channel: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to events on the specified channel.
        
        Args:
            channel: Event channel name
            callback: Function to call when an event is received
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if channel not in cls._subscribers:
                cls._subscribers[channel] = []
                
            cls._subscribers[channel].append(callback)
            logger.info(f"Subscribed to channel {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            return False
    
    @classmethod
    def get_latest_events(cls, channel: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest events from the specified channel.
        
        Args:
            channel: Event channel name
            limit: Maximum number of events to retrieve
            
        Returns:
            List of event dictionaries, newest first
        """
        try:
            events = EventModel.query.filter_by(channel=channel).order_by(
                EventModel.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': event.id,
                    'channel': event.channel,
                    'data': event.data,
                    'created_at': event.created_at.isoformat() if event.created_at else None
                }
                for event in events
            ]
        except Exception as e:
            logger.error(f"Failed to get latest events from channel {channel}: {e}")
            return []

# Export functions for backward compatibility
def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to the specified channel.
    
    Args:
        channel: Event channel name
        data: Event data to publish
        
    Returns:
        True if successful, False otherwise
    """
    return EventSystem.publish(channel, data)

def subscribe_to_events(channel: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
    """
    Subscribe to events on the specified channel.
    
    Args:
        channel: Event channel name
        callback: Function to call when an event is received
        
    Returns:
        True if successful, False otherwise
    """
    return EventSystem.subscribe(channel, callback)

def get_latest_events(channel: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the latest events from the specified channel.
    
    Args:
        channel: Event channel name
        limit: Maximum number of events to retrieve
        
    Returns:
        List of event dictionaries, newest first
    """
    return EventSystem.get_latest_events(channel, limit)