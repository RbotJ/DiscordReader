"""
Event System Module

This module provides a unified interface for the event system,
supporting both old and new code patterns during the transition
from Redis to PostgreSQL.
"""
import logging
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime
import enum

from common.db import db
from common.db_models import EventModel
from .compat import (
    EventClient, 
    ensure_event_system, 
    publish_event as _publish_event,
    get_latest_events
)

logger = logging.getLogger(__name__)

class EventChannels(enum.Enum):
    """Enumeration of event channels."""
    # Core system events
    SYSTEM = "system"
    # Discord-related events
    DISCORD_MESSAGE = "discord:message"
    DISCORD_SETUP_MESSAGE = "discord:setup_message"
    # Market data events
    TICKER_DATA = "market:ticker_data"
    PRICE_ALERT = "market:price_alert"
    CANDLE_PATTERN = "market:candle_pattern"
    # Setup-related events
    SETUP_CREATED = "setup:created"
    SETUP_UPDATED = "setup:updated"
    SETUP_TRIGGERED = "setup:triggered"
    # Trade-related events
    TRADE_EXECUTED = "trade:executed"
    TRADE_FILLED = "trade:filled"
    TRADE_CANCELED = "trade:canceled"

def initialize_event_system() -> bool:
    """
    Initialize the event system.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure database is ready
        ensure_event_system()
        logger.info("Event system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize event system: {e}")
        return False

def publish_event(channel: EventChannels, data: Dict[str, Any]) -> bool:
    """
    Publish an event to the specified channel.
    
    Args:
        channel: The channel to publish to (use EventChannels enum)
        data: The data to publish
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if isinstance(channel, EventChannels):
            channel_name = channel.value
        else:
            channel_name = str(channel)
            
        return _publish_event(channel_name, data)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        return False

def store_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    Store an event in the database without publishing.
    
    Args:
        channel: The channel associated with the event
        data: The event data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create event manually to avoid constructor issues
        event = EventModel()
        event.channel = channel
        event.data = data
        event.created_at = datetime.utcnow()
        
        db.session.add(event)
        db.session.commit()
        
        logger.debug(f"Stored event in channel {channel}")
        return True
    except Exception as e:
        logger.error(f"Failed to store event: {e}")
        db.session.rollback()
        return False

def poll_events(channel: str, after_timestamp: Optional[datetime] = None, 
               limit: int = 100) -> List[Dict[str, Any]]:
    """
    Poll for events on the specified channel.
    
    Args:
        channel: The channel to poll
        after_timestamp: Only return events after this timestamp
        limit: Maximum number of events to return
        
    Returns:
        List of events
    """
    try:
        query = db.session.query(EventModel).filter(
            EventModel.channel == channel
        )
        
        if after_timestamp:
            query = query.filter(EventModel.created_at > after_timestamp)
            
        events = query.order_by(
            EventModel.created_at.asc()
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
        logger.error(f"Failed to poll events: {e}")
        return []
        
def get_latest_event_id(channel: Optional[Union[str, EventChannels]] = None) -> int:
    """
    Get the latest event ID for a specific channel or across all channels.
    
    Args:
        channel: The specific channel to check, or None for all channels
        
    Returns:
        The latest event ID, or 0 if no events exist
    """
    try:
        query = db.session.query(EventModel.id)
        
        if channel:
            if isinstance(channel, EventChannels):
                channel_name = channel.value
            else:
                channel_name = str(channel)
                
            query = query.filter(EventModel.channel == channel_name)
            
        # Get the maximum ID
        latest_id = query.order_by(EventModel.id.desc()).first()
        
        if latest_id:
            return latest_id[0]
        return 0
    except Exception as e:
        logger.error(f"Failed to get latest event ID: {e}")
        return 0