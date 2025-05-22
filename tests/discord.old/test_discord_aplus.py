import logging
from datetime import datetime
from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import DiscordMessageModel

logger = logging.getLogger(__name__)

def test_discord_message():
    """Test publishing a Discord message"""
    message_data = {
        "message_id": "123",
        "content": "Test message",
        "timestamp": datetime.utcnow().isoformat()
    }

    success = publish_event(EventChannels.DISCORD_SETUP_MESSAGE, message_data)
    assert success, "Failed to publish event"