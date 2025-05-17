"""
Discord Message Publisher

This module focuses on publishing Discord messages to Redis for consumption by other
components without exposing direct Discord API dependencies to downstream services.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from common.redis_utils import publish_event
from common.event_constants import EventType

# Configure logger
logger = logging.getLogger(__name__)

# Define Redis channels
DISCORD_RAW_MESSAGE_CHANNEL = "events:discord:raw_messages"
DISCORD_SETUP_MESSAGE_CHANNEL = "events:discord:setup_messages"

def publish_raw_discord_message(message_id: str, content: str, author: str, 
                                timestamp: datetime, channel_id: str) -> bool:
    """
    Publish a raw Discord message to Redis.
    
    Args:
        message_id: Discord message ID
        content: Message content
        author: Message author username
        timestamp: Message timestamp
        channel_id: Discord channel ID
        
    Returns:
        bool: Success status
    """
    try:
        # Create message payload
        message_data = {
            "message_id": message_id,
            "content": content,
            "author": author,
            "timestamp": timestamp.isoformat(),
            "channel_id": channel_id
        }
        
        # Publish to Redis
        success = publish_event(
            channel=DISCORD_RAW_MESSAGE_CHANNEL,
            event_type=EventType.DISCORD_MESSAGE_RECEIVED,
            data=message_data
        )
        
        if success:
            logger.debug(f"Published Discord message {message_id} to Redis")
        else:
            logger.warning(f"Failed to publish Discord message {message_id} to Redis")
            
        return success
        
    except Exception as e:
        logger.error(f"Error publishing Discord message to Redis: {e}")
        return False

def publish_setup_message(message_id: str, content: str, author: str,
                         timestamp: datetime, channel_id: str, is_setup: bool = True) -> bool:
    """
    Publish a Discord message identified as a trading setup to Redis.
    
    Args:
        message_id: Discord message ID
        content: Message content
        author: Message author username
        timestamp: Message timestamp
        channel_id: Discord channel ID
        is_setup: Flag indicating if this is a trading setup message
        
    Returns:
        bool: Success status
    """
    try:
        # Create message payload
        message_data = {
            "message_id": message_id,
            "content": content,
            "author": author,
            "timestamp": timestamp.isoformat(),
            "channel_id": channel_id,
            "is_setup": is_setup
        }
        
        # Publish to Redis
        success = publish_event(
            channel=DISCORD_SETUP_MESSAGE_CHANNEL,
            event_type=EventType.DISCORD_SETUP_MESSAGE_RECEIVED,
            data=message_data
        )
        
        if success:
            logger.info(f"Published Discord setup message {message_id} to Redis")
        else:
            logger.warning(f"Failed to publish Discord setup message {message_id} to Redis")
            
        return success
        
    except Exception as e:
        logger.error(f"Error publishing Discord setup message to Redis: {e}")
        return False