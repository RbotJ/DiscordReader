"""
Discord Channels Models

SQLAlchemy models for Discord channel management and metadata storage.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from common.db import db
from common.utils import utc_now


class DiscordChannel(db.Model):
    """Discord Channel model for metadata and monitoring management."""
    
    __tablename__ = "discord_channels"

    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), nullable=False)
    guild_name = Column(String(255), nullable=True)
    channel_id = Column(String(50), nullable=False, unique=True, index=True)
    channel_name = Column(String(255), nullable=False, index=True)
    channel_type = Column(String(50), nullable=False, default="text")
    
    # Channel configuration flags
    is_listen = Column(Boolean, default=False)
    is_announce = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Metadata tracking
    last_message_id = Column(String(50), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, default=0)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    def __repr__(self):
        return f"<DiscordChannel(name={self.channel_name}, channel_id={self.channel_id})>"

    @classmethod
    def find_by_channel_id(cls, channel_id: str):
        """Find channel by Discord channel ID."""
        return cls.query.filter_by(channel_id=channel_id).first()

    @classmethod
    def find_by_name(cls, channel_name: str):
        """Find channel by name."""
        return cls.query.filter_by(channel_name=channel_name).first()

    @classmethod
    def find_active_channels(cls):
        """Find all active channels for monitoring."""
        return cls.query.filter_by(is_active=True).all()

    @classmethod
    def find_listening_channels(cls):
        """Find all channels marked for listening."""
        return cls.query.filter_by(is_listen=True, is_active=True).all()

    def update_last_seen(self, message_id: str = None):
        """Update last seen timestamp and optionally message ID."""
        self.last_seen = datetime.utcnow()
        if message_id:
            self.last_message_id = message_id
        self.updated_at = datetime.utcnow()