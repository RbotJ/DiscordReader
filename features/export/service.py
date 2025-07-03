import logging
from datetime import datetime
from typing import List, Optional, Dict

from common.db import db
from features.ingestion.models import DiscordMessageModel

logger = logging.getLogger(__name__)


def get_messages(
    channel_id: Optional[str] = None,
    author_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 1000,
) -> List[Dict[str, any]]:
    """Retrieve messages filtered by channel, author, and date range."""
    try:
        query = db.session.query(DiscordMessageModel)
        if channel_id:
            query = query.filter(DiscordMessageModel.channel_id == str(channel_id))
        if author_id:
            query = query.filter(DiscordMessageModel.author_id == str(author_id))
        if start:
            query = query.filter(DiscordMessageModel.timestamp >= start)
        if end:
            query = query.filter(DiscordMessageModel.timestamp <= end)
        query = query.order_by(DiscordMessageModel.timestamp.asc())
        if limit:
            query = query.limit(limit)
        messages = query.all()
        return [m.to_dict() for m in messages]
    except Exception as e:
        logger.error(f"Error exporting messages: {e}")
        return []
