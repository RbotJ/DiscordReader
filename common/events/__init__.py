"""
Events Package

This package provides event management functionality for the trading application.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .constants import EventChannels
from common.db import db

logger = logging.getLogger(__name__)

def publish_event(channel: str, payload: Dict[str, Any]) -> bool:
    """
    Publish an event to the specified channel.
    
    Args:
        channel: Event channel to publish to
        payload: Event payload data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Save event to database for later retrieval
        from common.db_models import EventModel
        
        event = EventModel(
            channel=channel,
            payload=payload,
            created_at=datetime.utcnow()
        )
        db.session.add(event)
        db.session.commit()
        
        logger.info(f"Published event to channel '{channel}'")
        return True
    except Exception as e:
        logger.error(f"Error publishing event: {e}")
        db.session.rollback()
        return False

def initialize_events():
    """Initialize the event system."""
    logger.info("Initializing event system...")
    return True

def get_latest_events(channel: Optional[str] = None, limit: int = 10) -> list:
    """
    Get the latest events from the specified channel.
    
    Args:
        channel: Optional channel to filter by
        limit: Maximum number of events to retrieve
        
    Returns:
        List of events
    """
    try:
        from common.db_models import EventModel
        
        query = EventModel.query.order_by(EventModel.created_at.desc())
        if channel:
            query = query.filter_by(channel=channel)
        
        events = query.limit(limit).all()
        return [event.to_dict() for event in events]
    except Exception as e:
        logger.error(f"Error retrieving events: {e}")
        return []