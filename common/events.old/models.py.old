"""
Events Feature Models

Database models for the unified events system.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from common.db import db

class EventModel(db.Model):
    """Event model for logging structured events in PostgreSQL."""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False, index=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Event(channel={self.channel}, created_at={self.created_at})>"