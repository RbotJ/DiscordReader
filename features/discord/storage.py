
"""
Discord Message Storage

Consolidated storage operations for Discord messages
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app import db
from .models import DiscordMessageModel

logger = logging.getLogger(__name__)

def validate_message(message: Dict) -> bool:
    """Validate required message fields exist"""
    required_fields = ['id', 'content', 'author', 'timestamp']
    return all(field in message for field in required_fields)

def store_message(message: Dict) -> Optional[int]:
    """
    Store Discord message in database
    
    Args:
        message: Message dictionary
        
    Returns:
        Stored message ID if successful, None otherwise
    """
    if not validate_message(message):
        logger.error(f"Invalid message format: {message}")
        return None

    if not message.get('content', '').strip():
        logger.warning("Skipping empty message")
        return None

    try:
        discord_message = DiscordMessageModel(
            message_id=message['id'],
            content=message['content'],
            author=message['author'],
            author_id=message.get('author_id', ''),
            channel_id=message.get('channel_id', ''),
            timestamp=datetime.fromisoformat(message['timestamp'])
        )

        db.session.add(discord_message)
        db.session.commit()

        logger.info(f"Stored Discord message {discord_message.id}")
        return discord_message.id

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error storing message: {e}")
        return None

def get_latest_message() -> Optional[Dict[str, Any]]:
    """Get the latest Discord message from database"""
    try:
        message = DiscordMessageModel.query.order_by(
            DiscordMessageModel.created_at.desc()
        ).first()
        
        if message:
            return {
                'id': message.id,
                'message_id': message.message_id,
                'content': message.content,
                'author': message.author,
                'timestamp': message.timestamp.isoformat() if message.timestamp else None
            }
        
        return None
    except Exception as e:
        logger.error(f"Failed to get latest message: {e}")
        return None

def get_message_count() -> int:
    """Get total message count"""
    try:
        return DiscordMessageModel.query.count()
    except Exception as e:
        logger.error(f"Failed to get message count: {e}")
        return 0
