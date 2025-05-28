"""
Discord Channels Model

This model represents Discord channels that the A+ Trading app monitors
for trading setup messages and announcements.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from common.db import db

class DiscordChannel(db.Model):
    """
    Discord channel configuration and metadata.
    
    This table stores information about Discord channels that the app
    monitors for trading messages, including their permissions and status.
    """
    __tablename__ = 'discord_channels_new'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), nullable=False, 
                     doc="Discord server (guild) ID where this channel exists")
    channel_id = Column(String(50), unique=True, nullable=False,
                       doc="Unique Discord channel ID")
    name = Column(String(255), nullable=False,
                 doc="Human-readable channel name")
    channel_type = Column(String(50), nullable=False, default='text',
                         doc="Type of Discord channel (text, voice, etc.)")
    is_listen = Column(Boolean, default=False,
                      doc="Whether to monitor this channel for messages")
    is_announce = Column(Boolean, default=False,
                        doc="Whether to send announcements to this channel")
    is_active = Column(Boolean, default=True,
                      doc="Whether this channel configuration is active")
    created_at = Column(DateTime, default=datetime.utcnow,
                       doc="When this channel was added to monitoring")
    last_seen = Column(DateTime, nullable=True,
                      doc="Last time a message was seen in this channel")

    def __repr__(self):
        return f"<DiscordChannel {self.name} ({self.channel_id})>"