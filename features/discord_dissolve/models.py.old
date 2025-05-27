"""
Discord Feature Models

Database models for Discord channel management and related data.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, UniqueConstraint
from datetime import datetime
from common.db import db

class DiscordChannelModel(db.Model):
    """Discord channel model for multi-channel management."""
    __tablename__ = 'discord_channels'

    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), nullable=False)
    channel_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    channel_type = Column(String(50), nullable=False, default='text')
    is_listen = Column(Boolean, nullable=False, default=False)
    is_announce = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('guild_id', 'channel_id', name='_guild_channel_uc'),)

    def __repr__(self):
        return f"<DiscordChannel(id={self.id}, name='{self.name}', channel_id='{self.channel_id}')>"