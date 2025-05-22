
"""
Event Publisher Module

Handles publishing events to the PostgreSQL event system.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from common.events.constants import EventChannels
from common.db import db
from common.db_models import EventModel

logger = logging.getLogger(__name__)

def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to the specified channel.
    
    Args:
        channel: Event channel name
        data: Event data to publish
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create and store event in database
        event = EventModel(
            channel=channel,
            data=data,
        )
        
        db.session.add(event)
        db.session.commit()
        
        logger.info(f"Published event to channel {channel}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        db.session.rollback()
        return False

def publish_discord_message(message_data: Dict[str, Any]) -> bool:
    """
    Publish Discord message event.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        return publish_event(EventChannels.DISCORD_MESSAGE, {
            'message_id': message_data.get('message_id', ''),
            'content': message_data.get('content', ''),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to publish Discord message event: {e}")
        return False

def publish_discord_setup(setup_data: Dict[str, Any]) -> bool:
    """
    Publish Discord setup event.
    
    Args:
        setup_data: Dictionary containing setup data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        return publish_event(EventChannels.SETUP_CREATED, {
            'setup_id': setup_data.get('id', ''),
            'content': setup_data.get('content', ''),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to publish Discord setup event: {e}")
        return False
