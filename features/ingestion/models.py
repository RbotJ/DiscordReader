"""
Ingestion Models Module

Database models for Discord message ingestion.
Contains the DiscordMessageModel for storing raw Discord messages.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import JSONB
from common.db import db
from common.utils import parse_discord_timestamp, utc_now

logger = logging.getLogger(__name__)


class DiscordMessageModel(db.Model):
    """
    Database model for storing Discord messages.
    
    This model represents raw Discord messages as they are ingested
    from the Discord API, before any parsing or processing.
    """
    
    __tablename__ = 'discord_messages'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(64), unique=True, nullable=False, index=True)
    channel_id = Column(String(64), nullable=False, index=True)
    author_id = Column(String(64), nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)  # Discord's sent time
    
    # Message metadata
    is_forwarded = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False, index=True)
    has_embeds = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    
    # JSON fields for additional data
    embed_data = Column(JSONB, nullable=True)
    attachment_data = Column(JSONB, nullable=True)
    raw_data = Column(JSONB, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    def __repr__(self) -> str:
        """String representation of the message model."""
        return f"<DiscordMessage {self.message_id} from {self.author_id}>"
    
    @classmethod
    def from_dict(cls, message_data: Dict[str, Any]) -> 'DiscordMessageModel':
        """
        Create a DiscordMessageModel instance from a message dictionary.
        Pure data structure creation - no database operations.
        
        Args:
            message_data: Dictionary containing message data from Discord API
            
        Returns:
            DiscordMessageModel: New model instance (not saved to database)
        """
        # Parse timestamp
        timestamp_str = message_data.get('timestamp')
        if isinstance(timestamp_str, str):
            timestamp = parse_discord_timestamp(timestamp_str)
        else:
            timestamp = timestamp_str or utc_now()
        
        # Create model instance (no database operations)
        return cls(
            message_id=str(message_data['id']),
            channel_id=str(message_data['channel_id']),
            author_id=str(message_data.get('author_id', message_data.get('author', ''))),
            content=str(message_data['content']),
            timestamp=timestamp,
            is_forwarded=message_data.get('is_forwarded', False),
            has_embeds=bool(message_data.get('embeds')),
            has_attachments=bool(message_data.get('attachments')),
            embed_data=message_data.get('embeds'),
            attachment_data=message_data.get('attachments'),
            raw_data=message_data
        )
    

    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the message
        """
        return {
            'id': self.id,
            'message_id': self.message_id,
            'channel_id': self.channel_id,
            'author_id': self.author_id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'is_forwarded': self.is_forwarded,
            'is_processed': self.is_processed,
            'has_embeds': self.has_embeds,
            'has_attachments': self.has_attachments,
            'embed_data': self.embed_data,
            'attachment_data': self.attachment_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_as_processed(self) -> None:
        """Mark this message as processed."""
        self.is_processed = True
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_unprocessed_messages(cls, limit: Optional[int] = None) -> list['DiscordMessageModel']:
        """
        Get unprocessed messages from the database.
        
        Args:
            limit: Optional limit on number of messages to return
            
        Returns:
            List[DiscordMessageModel]: Unprocessed messages
        """
        query = cls.query.filter_by(is_processed=False).order_by(cls.timestamp.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @classmethod
    def get_by_message_id(cls, message_id: str) -> Optional['DiscordMessageModel']:
        """
        Get message by Discord message ID.
        
        Args:
            message_id: Discord message ID
            
        Returns:
            Optional[DiscordMessageModel]: Message model or None if not found
        """
        return cls.query.filter_by(message_id=message_id).first()