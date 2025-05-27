
"""
Discord Events

Event publishing for Discord message operations
"""
import logging
from typing import Dict, Any
from datetime import datetime

from common.events import publish_event
from common.event_constants import EventType

logger = logging.getLogger(__name__)

def publish_message_stored_event(message_data: Dict[str, Any], stored_id: int) -> bool:
    """
    Publish event when Discord message is stored
    
    Args:
        message_data: Original message data
        stored_id: Database ID of stored message
        
    Returns:
        Success status
    """
    try:
        event_data = {
            'discord_message_id': stored_id,
            'message_id': message_data.get('id'),
            'content': message_data.get('content'),
            'author': message_data.get('author'),
            'timestamp': message_data.get('timestamp'),
            'source': 'discord'
        }
        
        return publish_event(EventType.MESSAGE_STORED, event_data)
        
    except Exception as e:
        logger.error(f"Failed to publish message stored event: {e}")
        return False

def publish_setup_detected_event(message_data: Dict[str, Any], setup_indicators: List[str]) -> bool:
    """
    Publish event when trading setup is detected in message
    
    Args:
        message_data: Message data
        setup_indicators: List of detected setup keywords
        
    Returns:
        Success status
    """
    try:
        event_data = {
            'message_id': message_data.get('id'),
            'content': message_data.get('content'),
            'setup_indicators': setup_indicators,
            'timestamp': message_data.get('timestamp'),
            'source': 'discord'
        }
        
        return publish_event(EventType.SETUP_DETECTED, event_data)
        
    except Exception as e:
        logger.error(f"Failed to publish setup detected event: {e}")
        return False
