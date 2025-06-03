"""
Centralized Event Publisher

Provides a unified interface for publishing events across the application.
Handles Flask application context properly to avoid context warnings.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)


def publish_event(
    event_type: str, 
    data: dict, 
    channel: str = "default", 
    source: str = None, 
    correlation_id: str = None
) -> bool:
    """
    Enhanced event publishing wrapper with proper Flask context handling.
    
    Args:
        event_type: Type of event (e.g. 'parsing.setup.parsed')
        data: Event data (dict)
        channel: Event channel (e.g. 'parsing:setup')
        source: Source service/module (e.g. 'discord_parser')
        correlation_id: UUID string for tracing related events
        
    Returns:
        bool: True if event published successfully, False otherwise
    """
    try:
        # Check if we have Flask application context
        if not has_app_context():
            logger.warning(f"Attempted to publish event {event_type} outside Flask application context")
            return False
        
        # Import here to avoid circular imports
        from sqlalchemy import text
        from common.db.session import db
        
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Create event data
        event_data = {
            'event_type': event_type,
            'channel': channel,
            'data': data,
            'source': source or 'unknown',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        
        # Insert into events table
        query = text("""
            INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
            VALUES (:event_type, :channel, :data, :source, :correlation_id, :created_at)
        """)
        
        db.session.execute(query, {
            'event_type': event_data['event_type'],
            'channel': event_data['channel'],
            'data': str(data) if not isinstance(data, str) else data,
            'source': event_data['source'],
            'correlation_id': event_data['correlation_id'],
            'created_at': event_data['created_at']
        })
        
        db.session.commit()
        
        logger.debug(f"Published event: {event_type} to channel: {channel}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")
        try:
            db.session.rollback()
        except:
            pass
        return False


def publish_event_safe(
    event_type: str, 
    data: dict, 
    channel: str = "default", 
    source: str = None, 
    correlation_id: str = None
) -> bool:
    """
    Safe event publishing that works both inside and outside Flask context.
    Falls back to logging when Flask context is not available.
    
    Args:
        event_type: Type of event
        data: Event data
        channel: Event channel
        source: Source service/module
        correlation_id: UUID string for tracing
        
    Returns:
        bool: True if published or logged successfully
    """
    if has_app_context():
        return publish_event(event_type, data, channel, source, correlation_id)
    else:
        # Log the event when Flask context is not available
        logger.info(f"Event [{event_type}] on channel [{channel}] from [{source}]: {data}")
        return True


def flush_event_buffer():
    """
    Flush any buffered events to the database.
    Useful for batch processing scenarios.
    """
    try:
        if has_app_context():
            from common.db import db
            db.session.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to flush event buffer: {e}")
        return False