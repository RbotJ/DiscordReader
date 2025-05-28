"""
Enhanced Event Publisher

Replaces basic event publishing with structured event bus using refined schema.
Provides correlation tracking and improved debugging capabilities.
"""
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from features.models.new_schema.events import Event
from common.db import db

logger = logging.getLogger(__name__)


class EventPublisher:
    """Enhanced event publisher with correlation tracking and structured data."""
    
    @staticmethod
    def publish_event(
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Optional[Event]:
        """
        Publish event to enhanced event bus.
        
        Args:
            channel: Event channel (e.g. 'setup:created')
            event_type: Event type (e.g. 'signal.triggered') 
            data: Structured event payload
            source: Source service/module
            correlation_id: UUID for tracing related events
            
        Returns:
            Optional[Event]: Published event or None if failed
        """
        try:
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            
            # Create and save event
            event = Event.create_event(
                channel=channel,
                event_type=event_type,
                data=data,
                source=source,
                correlation_id=correlation_id
            )
            
            db.session.add(event)
            db.session.commit()
            
            logger.info(f"Published event: {channel}.{event_type} from {source}")
            return event
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def publish_discord_message_stored(
        message_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Optional[Event]:
        """
        Publish Discord message stored event for ingestion pipeline.
        
        Args:
            message_data: Message information with channel_id, message_id, etc.
            correlation_id: Correlation UUID for tracing
            
        Returns:
            Optional[Event]: Published event
        """
        return EventPublisher.publish_event(
            channel='discord:message',
            event_type='message.stored',
            data=message_data,
            source='discord_ingestion',
            correlation_id=correlation_id
        )
    
    @staticmethod
    def publish_setup_parsed(
        setup_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Optional[Event]:
        """
        Publish setup parsed event from Discord message processing.
        
        Args:
            setup_data: Parsed setup information
            correlation_id: Correlation UUID linking to original message
            
        Returns:
            Optional[Event]: Published event
        """
        return EventPublisher.publish_event(
            channel='setup:created',
            event_type='setup.parsed',
            data=setup_data,
            source='discord_parser',
            correlation_id=correlation_id
        )
    
    @staticmethod
    def publish_channel_scan_completed(
        scan_results: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Optional[Event]:
        """
        Publish channel scan completed event from bot startup.
        
        Args:
            scan_results: Channel scan statistics
            correlation_id: Correlation UUID
            
        Returns:
            Optional[Event]: Published event
        """
        return EventPublisher.publish_event(
            channel='bot:startup',
            event_type='channels.scanned',
            data=scan_results,
            source='discord_bot',
            correlation_id=correlation_id
        )
    
    @staticmethod
    def generate_correlation_id() -> str:
        """
        Generate new correlation ID for event tracing.
        
        Returns:
            str: New UUID correlation ID
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def get_events_by_correlation(correlation_id: str) -> list[Event]:
        """
        Get all events with the same correlation ID for flow tracing.
        
        Args:
            correlation_id: Correlation UUID to search for
            
        Returns:
            list[Event]: Related events in chronological order
        """
        try:
            return Event.query.filter_by(
                correlation_id=uuid.UUID(correlation_id)
            ).order_by(Event.created_at.asc()).all()
            
        except Exception as e:
            logger.error(f"Error retrieving correlated events: {e}")
            return []