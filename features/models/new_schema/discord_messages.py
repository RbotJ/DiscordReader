"""
New Discord Messages Model

This model stores raw Discord messages before parsing.
Part of the new schema restructuring to improve setup parsing and data consistency.
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from common.db import db

class DiscordMessage(db.Model):
    """
    Discord Message Model
    
    Stores raw Discord messages that contain trading setups.
    This centralizes message storage and provides a clean foundation for parsing.
    
    Relationships:
    - Many-to-one with DiscordChannel (which channel this message came from)
    - One-to-many with TradeSetup (parsed setups from this message)
    """
    
    __tablename__ = 'discord_messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True, nullable=False, doc="Unique Discord message ID")
    channel_id = Column(String(50), ForeignKey("discord_channels.channel_id"), nullable=False, doc="Channel this message belongs to")
    author_id = Column(String(50), nullable=True, doc="Discord user ID of message author")
    content = Column(Text, nullable=True, doc="Raw message content")
    message_date = Column(Date, nullable=True, doc="Date the message was sent (trading day)")
    message_time = Column(DateTime(timezone=True), nullable=True, doc="Exact timestamp of message")
    processed = Column(Boolean, default=False, doc="Whether this message has been parsed")
    created_at = Column(DateTime, default=datetime.utcnow, doc="When message was stored in our database")
    
    # Relationships
    channel = relationship("DiscordChannel", back_populates="messages")
    trade_setups = relationship("TradeSetup", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DiscordMessage(id={self.id}, message_id='{self.message_id}', processed={self.processed})>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'channel_id': self.channel_id,
            'author_id': self.author_id,
            'content': self.content,
            'message_date': self.message_date.isoformat() if self.message_date else None,
            'message_time': self.message_time.isoformat() if self.message_time else None,
            'processed': self.processed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def mark_processed(self):
        """Mark this message as processed"""
        self.processed = True
        db.session.commit()
    
    @property
    def content_preview(self):
        """Get a preview of the message content (first 100 chars)"""
        if not self.content:
            return ""
        return self.content[:100] + "..." if len(self.content) > 100 else self.content