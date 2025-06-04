"""
Discord Bot Models

SQLAlchemy models for Discord channel management within the discord_bot vertical slice.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from common.db import db


class DiscordChannel(db.Model):
    """Discord Channel model for bot monitoring and management."""
    
    __tablename__ = "discord_channels"

    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), nullable=False)
    channel_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    channel_type = Column(String(50), nullable=False)  # e.g. "text"
    is_listen = Column(Boolean, default=False)
    is_announce = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DiscordChannel(name={self.name}, channel_id={self.channel_id})>"

    @classmethod
    def find_by_channel_id(cls, channel_id: str):
        """Find channel by Discord channel ID."""
        return cls.query.filter_by(channel_id=channel_id).first()

    @classmethod
    def find_active_channels(cls):
        """Find all active channels for monitoring."""
        return cls.query.filter_by(is_active=True).all()