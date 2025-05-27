
"""
Discord Message Publisher 

Publishes Discord messages to the PostgreSQL event system.
"""
import logging
from typing import Dict, Any
from datetime import datetime

from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import DiscordMessageModel

logger = logging.getLogger(__name__)

def publish_discord_message(message_data: Dict[str, Any]) -> bool:
    """
    Publish a Discord message to the event system and store in database.
    """
    try:
        # Store message in database
        message = DiscordMessageModel(
            message_id=message_data.get('id'),
            content=message_data.get('content'),
            channel_id=message_data.get('channel_id'),
            timestamp=datetime.utcnow(),
            meta_data=message_data
        )
        db.session.add(message)
        db.session.commit()

        # Publish event
        return publish_event(EventChannels.DISCORD_SETUP_MESSAGE, {
            'message_id': message_data.get('id'),
            'content': message_data.get('content'),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to publish Discord message: {e}")
        db.session.rollback()
        return False
