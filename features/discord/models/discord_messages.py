"""
Discord Messages Model

This model represents raw Discord messages collected by the ingestion system
for parsing and analysis of trading setups.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey
from common.db import db

class DiscordMessage(db.Model):
    """
    Raw Discord messages from monitored channels.
    
    This table stores the complete Discord message data before parsing,
    providing a clean audit trail of all ingested messages.
    """
    __tablename__ = 'discord_messages_new'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True, nullable=False,
                       doc="Unique Discord message ID")
    channel_id = Column(String(50), ForeignKey("discord_channels_new.channel_id"), nullable=False,
                       doc="Channel where this message was posted")
    author_id = Column(String(50), nullable=True,
                      doc="Discord user ID who posted the message")
    content = Column(Text, nullable=True,
                    doc="Full text content of the Discord message")
    message_date = Column(Date, nullable=True,
                         doc="Date when the message was posted (trading day)")
    message_time = Column(DateTime(timezone=True), nullable=True,
                         doc="Exact timestamp when message was posted")
    processed = Column(Boolean, default=False,
                      doc="Whether this message has been parsed for setups")
    created_at = Column(DateTime, default=datetime.utcnow,
                       doc="When this message was ingested by our system")

    def __repr__(self):
        return f"<DiscordMessage {self.message_id} from {self.channel_id}>"