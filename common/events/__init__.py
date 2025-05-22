"""
Event System Package

This package provides a PostgreSQL-based event system for publishing and subscribing to events.
"""
import json
import logging
from typing import Dict, Any, Optional, List, Callable

from common.db import db
from common.db_models import EventModel

# Create a logger for this module
logger = logging.getLogger(__name__)

class EventSystem:
    """Event system using PostgreSQL for storage and distribution."""
    
    @staticmethod
    def publish_event(channel: str, payload: Dict[str, Any]) -> bool:
        """
        Publish an event to a channel.
        
        Args:
            channel: The channel to publish to
            payload: The event payload
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create and store the event
            event = EventModel(
                channel=channel,
                payload=payload
            )
            
            db.session.add(event)
            db.session.commit()
            
            logger.info(f"Published event to channel '{channel}'")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_events(channel: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events from a channel.
        
        Args:
            channel: The channel to get events from
            limit: Maximum number of events to retrieve
            
        Returns:
            List of event dictionaries
        """
        try:
            events = EventModel.query.filter_by(channel=channel).order_by(
                EventModel.created_at.desc()
            ).limit(limit).all()
            
            return [event.to_dict() for event in events]
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

def initialize_events() -> bool:
    """
    Initialize the event system.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check that we can connect to the database
        EventModel.query.limit(1).all()
        logger.info("Event system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize event system: {e}")
        return False

# Export the EventSystem class and initialize_events function
__all__ = ['EventSystem', 'initialize_events']