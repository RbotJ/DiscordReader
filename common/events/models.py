"""
Event System Database Models

Single Event model for PostgreSQL event bus system.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from common.db.session import db


class Event(db.Model):
    """
    Single Event model for the PostgreSQL event bus.
    Stores all events across the trading application.
    """
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)
    payload = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)
    correlation_id = Column(String(36), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Event {self.id}: {self.event_type} on {self.channel}>"
    
    def to_dict(self):
        """Convert event to dictionary representation."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'channel': self.channel,
            'payload': self.payload,
            'source': self.source,
            'correlation_id': self.correlation_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }