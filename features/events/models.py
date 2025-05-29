"""
Events Models

SQLAlchemy models for the enhanced events system within the events vertical slice.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from common.db import db


class Event(db.Model):
    """Event model for structured event logging and tracking."""
    
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    channel = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    source = Column(String(100), nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)  # Proper UUID type
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Event(channel={self.channel}, event_type={self.event_type}, created_at={self.created_at})>"

    @classmethod
    def find_by_channel(cls, channel: str, limit: int = 100):
        """Find events by channel."""
        return cls.query.filter_by(channel=channel).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def find_by_correlation_id(cls, correlation_id: str):
        """Find all events with the same correlation ID for flow tracking."""
        return cls.query.filter_by(correlation_id=correlation_id).order_by(cls.created_at.asc()).all()