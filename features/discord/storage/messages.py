"""
Discord Message Storage

This module provides functions for storing and retrieving Discord messages
from the PostgreSQL database. It maintains a history of messages and provides
statistics about message volume and timestamps.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from sqlalchemy import desc, func, and_
from common.db import db
from common.db_models import DiscordMessageModel
from common.events import publish_event, EventChannels

logger = logging.getLogger(__name__)

def store_message(message_data: Dict[str, Any]) -> bool:
    """
    Store a Discord message in the database.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create message using SQLAlchemy ORM
        message = DiscordMessageModel()
        message.channel_id = message_data['channel_id']
        message.message_id = message_data['message_id']
        message.content = message_data['content']
        message.author = message_data.get('author', 'Unknown')
        message.created_at = datetime.utcnow()
        db.session.add(message)
        db.session.commit()

        # Publish event for other components
        publish_event(EventChannels.DISCORD_MESSAGE, {
            'message_id': message_data['message_id'],
            'content': message_data['content'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Stored Discord message {message_data['message_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to store Discord message: {e}")
        db.session.rollback()
        return False

def get_latest_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest Discord message from the database.
    
    Returns:
        Dictionary containing message data or None if not found
    """
    try:
        message = db.session.query(DiscordMessageModel).order_by(
            DiscordMessageModel.created_at.desc()
        ).first()
        
        if not message:
            logger.warning("No Discord messages found in database")
            return None
            
        return {
            'id': message.id,
            'message_id': message.message_id,
            'channel_id': message.channel_id,
            'content': message.content,
            'author': message.author,
            'created_at': message.created_at.isoformat() if message.created_at else None
        }
    except Exception as e:
        logger.error(f"Failed to get latest message: {e}")
        return None

def get_message_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get the message history from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of message dictionaries, newest first
    """
    try:
        messages = db.session.query(DiscordMessageModel).order_by(
            DiscordMessageModel.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for message in messages:
            result.append({
                'id': message.id,
                'message_id': message.message_id,
                'channel_id': message.channel_id,
                'content': message.content,
                'author': message.author,
                'created_at': message.created_at.isoformat() if message.created_at else None
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get message history: {e}")
        return []

def get_message_count() -> int:
    """
    Get the total number of messages in the database.
    
    Returns:
        Integer count of messages
    """
    try:
        return db.session.query(DiscordMessageModel).count()
    except Exception as e:
        logger.error(f"Failed to get message count: {e}")
        return 0

def get_message_stats() -> Dict[str, Any]:
    """
    Get statistics about stored messages from the database.
    
    Returns:
        Dictionary containing message statistics
    """
    try:
        total = db.session.query(DiscordMessageModel).count()
        
        # Get oldest and newest message timestamps
        newest = db.session.query(DiscordMessageModel).order_by(
            DiscordMessageModel.created_at.desc()
        ).first()
        
        oldest = db.session.query(DiscordMessageModel).order_by(
            DiscordMessageModel.created_at.asc()
        ).first()
        
        # Get count of messages in the last 24 hours
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_count = db.session.query(DiscordMessageModel).filter(
            DiscordMessageModel.created_at >= day_ago
        ).count()
        
        # Count messages by author
        author_counts = db.session.query(
            DiscordMessageModel.author, 
            func.count(DiscordMessageModel.id)
        ).group_by(
            DiscordMessageModel.author
        ).all()
        
        authors = {author: count for author, count in author_counts}
        
        return {
            'total_messages': total,
            'newest_message': newest.created_at.isoformat() if newest and newest.created_at else None,
            'oldest_message': oldest.created_at.isoformat() if oldest and oldest.created_at else None,
            'last_24h_count': recent_count,
            'author_counts': authors
        }
    except Exception as e:
        logger.error(f"Failed to get message stats: {e}")
        return {
            'total_messages': 0,
            'newest_message': None,
            'oldest_message': None,
            'last_24h_count': 0,
            'author_counts': {}
        }