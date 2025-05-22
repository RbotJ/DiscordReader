
"""
Event Publisher Module

Handles publishing events to the PostgreSQL event system.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from common.events import publish_event
from common.event_constants import EventChannels
from common.db import db
from common.db_models import EventModel

logger = logging.getLogger(__name__)

def publish_discord_message(message_data: Dict[str, Any]) -> bool:
    """Publish Discord message event"""
    try:
        return publish_event(EventChannels.DISCORD_SETUP_MESSAGE, {
            'message_id': message_data.get('id'),
            'content': message_data.get('content'),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to publish Discord message event: {e}")
        return False

def publish_discord_setup(setup_data: Dict[str, Any]) -> bool:
    """Publish Discord setup event"""
    try:
        return publish_event(EventChannels.SETUP_CREATED, {
            'setup_id': setup_data.get('id'),
            'content': setup_data.get('content'),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to publish Discord setup event: {e}")
        return False
