"""
Discord Message Storage Module

This module provides functions for storing and retrieving Discord messages
in the PostgreSQL database.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, desc, select, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database connection
def get_db_engine():
    """Get SQLAlchemy engine for database connection."""
    try:
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return None
        
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        return None

def get_db_session():
    """Get SQLAlchemy session for database operations."""
    engine = get_db_engine()
    if not engine:
        return None
        
    Session = sessionmaker(bind=engine)
    return Session()

# Database model for Discord messages
Base = declarative_base()

class DiscordMessageModel(Base):
    """Model for storing Discord messages."""
    
    __tablename__ = 'discord_messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True, nullable=False)
    author = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    channel_id = Column(String(50), nullable=False)
    channel_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False)
    attachments = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'author': self.author,
            'content': self.content,
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'attachments': self.attachments or [],
            'metadata': self.metadata or {}
        }

def init_db():
    """Initialize the database schema if needed."""
    engine = get_db_engine()
    if engine:
        Base.metadata.create_all(engine)
        logger.info("Discord message storage database initialized")
    else:
        logger.error("Failed to initialize Discord message storage database")

def store_message(message_data: Dict[str, Any]) -> bool:
    """
    Store a Discord message in the database.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure database is initialized
        init_db()
        
        # Extract relevant data
        message_id = message_data.get('id')
        if not message_id:
            logger.error("Cannot store message: Missing message ID")
            return False
            
        # Check if message already exists
        session = get_db_session()
        if not session:
            logger.error("Cannot store message: Database session not available")
            return False
            
        existing = session.execute(
            select(DiscordMessageModel).where(DiscordMessageModel.message_id == message_id)
        ).scalar_one_or_none()
        
        if existing:
            logger.info(f"Message {message_id} already exists in database")
            return True
            
        # Parse created_at timestamp
        created_at = message_data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()
            
        # Create new message record
        new_message = DiscordMessageModel(
            message_id=message_id,
            author=message_data.get('author', 'Unknown'),
            content=message_data.get('content', ''),
            channel_id=message_data.get('channel_id', ''),
            channel_name=message_data.get('channel_name', ''),
            created_at=created_at,
            attachments=message_data.get('attachments', []),
            metadata=message_data.get('metadata', {})
        )
        
        session.add(new_message)
        session.commit()
        
        logger.info(f"Message {message_id} stored successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to store message: {e}")
        if session:
            session.rollback()
        return False
    finally:
        if session:
            session.close()

def get_latest_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest Discord message from the database.
    
    Returns:
        dict: Message data or None if not found
    """
    try:
        session = get_db_session()
        if not session:
            logger.error("Cannot get latest message: Database session not available")
            return None
            
        latest = session.execute(
            select(DiscordMessageModel).order_by(desc(DiscordMessageModel.created_at)).limit(1)
        ).scalar_one_or_none()
        
        if latest:
            return latest.to_dict()
        else:
            logger.warning("No Discord messages found in database")
            return None
    except Exception as e:
        logger.error(f"Failed to get latest message: {e}")
        return None
    finally:
        if session:
            session.close()

def get_message_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get the message history from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
        
    Returns:
        list: List of message dictionaries, newest first
    """
    try:
        session = get_db_session()
        if not session:
            logger.error("Cannot get message history: Database session not available")
            return []
            
        messages = session.execute(
            select(DiscordMessageModel)
            .order_by(desc(DiscordMessageModel.created_at))
            .limit(limit)
        ).scalars().all()
        
        return [msg.to_dict() for msg in messages]
    except Exception as e:
        logger.error(f"Failed to get message history: {e}")
        return []
    finally:
        if session:
            session.close()

def get_message_count() -> int:
    """
    Get the total number of messages in the database.
    
    Returns:
        int: Count of messages
    """
    try:
        session = get_db_session()
        if not session:
            logger.error("Cannot get message count: Database session not available")
            return 0
            
        count = session.execute(
            select(DiscordMessageModel)
        ).count()
        
        return count
    except Exception as e:
        logger.error(f"Failed to get message count: {e}")
        return 0
    finally:
        if session:
            session.close()

def get_message_stats() -> Dict[str, Any]:
    """
    Get statistics about stored messages from the database.
    
    Returns:
        dict: Dictionary containing message statistics
    """
    session = None
    try:
        session = get_db_session()
        if not session:
            logger.error("Cannot get message stats: Database session not available")
            return {
                'count': 0,
                'oldest': None,
                'newest': None,
                'channels': {}
            }
            
        # Get count
        count_result = session.query(DiscordMessageModel).count()
        count = count_result if count_result is not None else 0
        
        # Get oldest and newest
        oldest = session.execute(
            select(DiscordMessageModel).order_by(DiscordMessageModel.created_at).limit(1)
        ).scalar_one_or_none()
        
        newest = session.execute(
            select(DiscordMessageModel).order_by(desc(DiscordMessageModel.created_at)).limit(1)
        ).scalar_one_or_none()
        
        # Get channel stats
        channels = {}
        channel_query = select(
            DiscordMessageModel.channel_name, 
            func.count(DiscordMessageModel.id).label('count')
        ).group_by(DiscordMessageModel.channel_name)
        
        channel_results = session.execute(channel_query).all()
        
        for row in channel_results:
            channel_name = row[0] or "Unknown"
            count_val = row[1] or 0
            channels[channel_name] = count_val
            
        return {
            'count': count,
            'oldest': oldest.to_dict() if oldest else None,
            'newest': newest.to_dict() if newest else None,
            'channels': channels
        }
    except Exception as e:
        logger.error(f"Failed to get message stats: {e}")
        return {
            'count': 0,
            'oldest': None,
            'newest': None,
            'channels': {},
            'error': str(e)
        }
    finally:
        if session:
            session.close()