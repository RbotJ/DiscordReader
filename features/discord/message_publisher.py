"""
Discord Message Publisher

This module focuses on publishing Discord messages for consumption by other
components without exposing direct Discord API dependencies to downstream services.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from common.events import publish_event
from common.event_constants import (
    DISCORD_RAW_MESSAGE_CHANNEL,
    DISCORD_SETUP_MESSAGE_CHANNEL,
    EventType
)

logger = logging.getLogger(__name__)

def publish_raw_discord_message(message_id: str, content: str, author: str, 
                              timestamp: datetime, channel_id: str) -> bool:
    """
    Publish a raw Discord message to the event system.
    """
    try:
        message_data = {
            "message_id": message_id,
            "content": content,
            "author": author,
            "timestamp": timestamp.isoformat(),
            "channel_id": channel_id
        }

        success = publish_event(
            channel=DISCORD_RAW_MESSAGE_CHANNEL,
            event_type=EventType.DISCORD_MESSAGE_RECEIVED,
            data=message_data
        )

        if success:
            logger.debug(f"Published Discord message {message_id}")
        else:
            logger.warning(f"Failed to publish Discord message {message_id}")

        return success

    except Exception as e:
        logger.error(f"Error publishing Discord message: {e}")
        return False

def publish_setup_message(message_id: str, content: str, author: str,
                         timestamp: datetime, channel_id: str, is_setup: bool = True) -> bool:
    """
    Publish a Discord message identified as a trading setup.
    """
    try:
        message_data = {
            "message_id": message_id,
            "content": content,
            "author": author,
            "timestamp": timestamp.isoformat(),
            "channel_id": channel_id,
            "is_setup": is_setup
        }

        success = publish_event(
            channel=DISCORD_SETUP_MESSAGE_CHANNEL,
            event_type=EventType.DISCORD_SETUP_MESSAGE_RECEIVED,
            data=message_data
        )

        if success:
            logger.info(f"Published Discord setup message {message_id}")
        else:
            logger.warning(f"Failed to publish Discord setup message {message_id}")

        return success

    except Exception as e:
        logger.error(f"Error publishing Discord setup message: {e}")
        return False