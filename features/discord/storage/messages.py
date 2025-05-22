"""
Discord Messages Storage

This module provides storage functionality for Discord messages.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import select, func

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy base
Base = declarative_base()

class DiscordMessageModel(Base):
    """Discord message database model."""
    __tablename__ = 'discord_messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    author_id = Column(String(50), nullable=False)
    channel_id = Column(String(50), nullable=False)
    channel_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DiscordMessage(id={self.id}, message_id={self.message_id}, author={self.author})>"

# Database connection
_engine = None
_Session = None

def init_db():
    """Initialize database connection and create tables if they don't exist."""
    global _engine, _Session
    
    if _engine is not None:
        return
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("No DATABASE_URL environment variable found")
        return False
    
    try:
        _engine = create_engine(db_url)
        Base.metadata.create_all(_engine)
        _Session = sessionmaker(bind=_engine)
        logger.info("Discord message database initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def store_message(message_data: Dict[str, Any]) -> bool:
    """
    Store a Discord message in the database.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not _engine or not _Session:
        if not init_db():
            return False
    
    # Check if message data has all required fields
    required_fields = ['id', 'content', 'author', 'author_id', 'channel_id', 'timestamp']
    for field in required_fields:
        if field not in message_data:
            logger.error(f"Message data missing required field: {field}")
            return False
    
    # Parse timestamp if it's a string
    timestamp = message_data['timestamp']
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            logger.error(f"Invalid timestamp format: {timestamp}")
            return False
    
    # Create message model
    message = DiscordMessageModel(
        message_id=message_data['id'],
        content=message_data['content'],
        author=message_data['author'],
        author_id=message_data['author_id'],
        channel_id=message_data['channel_id'],
        channel_name=message_data.get('channel_name'),
        timestamp=timestamp,
        message_metadata=message_data.get('raw') or message_data.get('metadata')
    )
    
    # Save to database
    session = _Session()
    try:
        # Check if message already exists
        existing = session.query(DiscordMessageModel).filter_by(message_id=message_data['id']).first()
        if existing:
            logger.info(f"Message {message_data['id']} already exists, skipping")
            session.close()
            return True
        
        session.add(message)
        session.commit()
        logger.info(f"Stored Discord message {message_data['id']}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to store message: {e}")
        return False
    finally:
        session.close()

def get_latest_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest Discord message from the database.
    
    Returns:
        Dictionary containing message data or None if not found
    """
    if not _engine or not _Session:
        if not init_db():
            return None
    
    session = _Session()
    try:
        query = session.query(DiscordMessageModel).order_by(DiscordMessageModel.timestamp.desc()).first()
        if not query:
            logger.warning("No messages found in database")
            return None
        
        message_data = {
            'id': query.message_id,
            'content': query.content,
            'author': query.author,
            'author_id': query.author_id,
            'channel_id': query.channel_id,
            'channel_name': query.channel_name,
            'timestamp': query.timestamp.isoformat(),
            'metadata': query.message_metadata
        }
        
        return message_data
    except Exception as e:
        logger.error(f"Failed to get latest message: {e}")
        return None
    finally:
        session.close()

def get_message_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get the message history from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of message dictionaries, newest first
    """
    if not _engine or not _Session:
        if not init_db():
            return []
    
    session = _Session()
    try:
        query = session.query(DiscordMessageModel).order_by(DiscordMessageModel.timestamp.desc()).limit(limit).all()
        
        messages = []
        for msg in query:
            message_data = {
                'id': msg.message_id,
                'content': msg.content,
                'author': msg.author,
                'author_id': msg.author_id,
                'channel_id': msg.channel_id,
                'channel_name': msg.channel_name,
                'timestamp': msg.timestamp.isoformat(),
                'metadata': msg.message_metadata
            }
            messages.append(message_data)
        
        return messages
    except Exception as e:
        logger.error(f"Failed to get message history: {e}")
        return []
    finally:
        session.close()

def get_message_count() -> int:
    """
    Get the total number of messages in the database.
    
    Returns:
        Integer count of messages
    """
    if not _engine or not _Session:
        if not init_db():
            return 0
    
    session = _Session()
    try:
        count = session.query(func.count(DiscordMessageModel.id)).scalar()
        return count or 0
    except Exception as e:
        logger.error(f"Failed to get message count: {e}")
        return 0
    finally:
        session.close()

def get_message_stats() -> Dict[str, Any]:
    """
    Get statistics about stored messages from the database.
    
    Returns:
        Dictionary containing message statistics
    """
    if not _engine or not _Session:
        if not init_db():
            return {'count': 0, 'oldest': None, 'newest': None, 'authors': {}, 'channels': {}}
    
    session = _Session()
    try:
        # Get total count
        count = session.query(func.count(DiscordMessageModel.id)).scalar() or 0
        
        # Get oldest and newest timestamps
        oldest = session.query(DiscordMessageModel.timestamp).order_by(DiscordMessageModel.timestamp.asc()).first()
        newest = session.query(DiscordMessageModel.timestamp).order_by(DiscordMessageModel.timestamp.desc()).first()
        
        # Get author counts
        author_counts = {}
        authors = session.query(DiscordMessageModel.author, func.count(DiscordMessageModel.id)).group_by(DiscordMessageModel.author).all()
        for author, count in authors:
            author_counts[author] = count
        
        # Get channel counts
        channel_counts = {}
        channels = session.query(DiscordMessageModel.channel_name, func.count(DiscordMessageModel.id)).group_by(DiscordMessageModel.channel_name).all()
        for channel, count in channels:
            channel_name = channel or 'unknown'
            channel_counts[channel_name] = count
        
        return {
            'count': count,
            'oldest': oldest[0].isoformat() if oldest and oldest[0] else None,
            'newest': newest[0].isoformat() if newest and newest[0] else None,
            'authors': author_counts,
            'channels': channel_counts
        }
    except Exception as e:
        logger.error(f"Failed to get message stats: {e}")
        return {'count': 0, 'oldest': None, 'newest': None, 'authors': {}, 'channels': {}}
    finally:
        session.close()