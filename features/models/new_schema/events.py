"""
Enhanced Events Model

Refined event table schema for PostgreSQL event bus with improved tracing
and analytics capabilities. Matches new schema requirements.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from common.db import db


class Event(db.Model):
    """
    Enhanced event model for PostgreSQL event bus.
    
    Provides structured event logging with correlation tracking
    and rich metadata for debugging and analytics.
    """
    
    __tablename__ = 'events'
    __table_args__ = {'extend_existing': True}
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event identification
    channel = Column(String(50), nullable=False, index=True)           # e.g. 'setup:created'
    event_type = Column(String(100), nullable=False, index=True)       # e.g. 'signal.triggered'
    
    # Tracing and debugging
    source = Column(String(100), nullable=True, index=True)            # e.g. 'discord_parser'
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # for flow tracing
    
    # Event payload
    data = Column(JSONB, nullable=False)                               # structured payload
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        index=True
    )
    
    def __repr__(self) -> str:
        """String representation of the event."""
        return f"<Event {self.id}: {self.channel}.{self.event_type}>"
    
    @classmethod
    def create_event(
        cls,
        channel: str,
        event_type: str,
        data: dict,
        source: str = None,
        correlation_id: str = None
    ) -> 'Event':
        """
        Create a new event with proper structure.
        
        Args:
            channel: Event channel (e.g. 'setup:created')
            event_type: Event type (e.g. 'signal.triggered')
            data: Structured event payload
            source: Source service/module (e.g. 'discord_parser')
            correlation_id: UUID for tracing related events
            
        Returns:
            Event: New event instance
        """
        # Convert string UUID to UUID object if provided
        uuid_obj = None
        if correlation_id:
            if isinstance(correlation_id, str):
                uuid_obj = uuid.UUID(correlation_id)
            else:
                uuid_obj = correlation_id
        
        return cls(
            channel=channel,
            event_type=event_type,
            source=source,
            correlation_id=uuid_obj,
            data=data
        )
    
    @classmethod
    def publish_setup_created(
        cls, 
        setup_data: dict, 
        source: str = 'discord_parser',
        correlation_id: str = None
    ) -> 'Event':
        """
        Publish setup created event.
        
        Args:
            setup_data: Setup information
            source: Source of the event
            correlation_id: Correlation UUID
            
        Returns:
            Event: Published event
        """
        return cls.create_event(
            channel='setup:created',
            event_type='setup.parsed',
            data=setup_data,
            source=source,
            correlation_id=correlation_id
        )
    
    @classmethod
    def publish_message_stored(
        cls,
        message_data: dict,
        source: str = 'discord_ingestion',
        correlation_id: str = None
    ) -> 'Event':
        """
        Publish message stored event.
        
        Args:
            message_data: Message information
            source: Source of the event
            correlation_id: Correlation UUID
            
        Returns:
            Event: Published event
        """
        return cls.create_event(
            channel='discord:message',
            event_type='message.stored',
            data=message_data,
            source=source,
            correlation_id=correlation_id
        )
    
    @classmethod
    def publish_signal_triggered(
        cls,
        signal_data: dict,
        source: str = 'signal_monitor',
        correlation_id: str = None
    ) -> 'Event':
        """
        Publish signal triggered event.
        
        Args:
            signal_data: Signal information
            source: Source of the event
            correlation_id: Correlation UUID
            
        Returns:
            Event: Published event
        """
        return cls.create_event(
            channel='signal:triggered',
            event_type='signal.activated',
            data=signal_data,
            source=source,
            correlation_id=correlation_id
        )
    
    def to_dict(self) -> dict:
        """
        Convert event to dictionary representation.
        
        Returns:
            dict: Event data
        """
        return {
            'id': self.id,
            'channel': self.channel,
            'event_type': self.event_type,
            'source': self.source,
            'correlation_id': str(self.correlation_id) if self.correlation_id is not None else None,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None
        }