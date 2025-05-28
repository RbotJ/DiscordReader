"""
New Discord Channels Model

This model represents Discord channels that the bot monitors for trading setups.
Part of the new schema restructuring to improve setup parsing and data consistency.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from common.db import db

class DiscordChannel(db.Model):
    """
    Discord Channel Model
    
    Stores information about Discord channels that are monitored for trading messages.
    This replaces the old fragmented approach to channel management.
    
    Relationships:
    - One-to-many with DiscordMessage (messages from this channel)
    """
    
    __tablename__ = 'discord_channels'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), nullable=False, doc="Discord server/guild ID")
    channel_id = Column(String(50), unique=True, nullable=False, doc="Unique Discord channel ID")
    name = Column(String(255), nullable=False, doc="Human-readable channel name")
    channel_type = Column(String(50), nullable=False, doc="Channel type (text, voice, etc.)")
    is_listen = Column(Boolean, default=False, doc="Whether bot listens to this channel")
    is_announce = Column(Boolean, default=False, doc="Whether bot announces to this channel")
    is_active = Column(Boolean, default=True, doc="Whether channel is currently active")
    created_at = Column(DateTime, default=datetime.utcnow, doc="When channel was added to monitoring")
    last_seen = Column(DateTime, nullable=True, doc="Last time activity was seen in channel")
    
    # Relationships
    messages = relationship("DiscordMessage", back_populates="channel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DiscordChannel(id={self.id}, name='{self.name}', channel_id='{self.channel_id}')>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'channel_id': self.channel_id,
            'name': self.name,
            'channel_type': self.channel_type,
            'is_listen': self.is_listen,
            'is_announce': self.is_announce,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }