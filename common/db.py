"""
Database Utilities

A module providing a shared SQLAlchemy database instance and common database operations.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
from sqlalchemy import text

# Setup logging
logger = logging.getLogger(__name__)

# Create a SQLAlchemy instance
db = SQLAlchemy()

def initialize_db(app):
    """Initialize database with app context."""
    try:
        db.init_app(app)
        with app.app_context():
            db.create_all()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def publish_event(event_type: str, payload: dict, channel: str = "default", source: str = None, correlation_id: str = None):
    """
    Enhanced event publishing wrapper with richer metadata and traceability.
    
    Args:
        event_type: Type of event (e.g. 'parsing.setup.parsed')
        payload: Event data payload (dict)
        channel: Event channel (e.g. 'parsing:setup')
        source: Source service/module (e.g. 'discord_parser')
        correlation_id: UUID string for tracing related events
        
    Returns:
        bool: True if event published successfully, False otherwise
    """
    from flask import has_app_context
    
    if not has_app_context():
        import logging
        logging.warning(f"Attempted to publish event {event_type} outside Flask application context")
        return False
    
    try:
        from common.events.enhanced_publisher import EventPublisher
        import uuid
        
        # Generate correlation ID if not provided
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        # Validate correlation ID format
        if correlation_id and isinstance(correlation_id, str):
            try:
                uuid.UUID(correlation_id)  # Validate UUID format
            except ValueError:
                logger.warning(f"Invalid correlation_id format: {correlation_id}, generating new one")
                correlation_id = str(uuid.uuid4())
        
        # Add metadata to payload
        enhanced_payload = {
            **payload,
            'published_at': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id
        }
        
        event = EventPublisher.publish_event(
            channel=channel,
            event_type=event_type,
            data=enhanced_payload,
            source=source or 'unknown',
            correlation_id=correlation_id
        )
        
        if event:
            logger.debug(f"Event published: {channel}.{event_type} [{correlation_id[:8]}...]")
            return True
        else:
            logger.error(f"Failed to publish event: {channel}.{event_type}")
            return False
            
    except Exception as e:
        logger.error(f"Error in enhanced event publishing: {e}")
        return False

def execute_query(query, params=None, fetch_one=False):
    """
    Execute a raw SQL query safely.

    Args:
        query (str): SQL query to execute
        params (tuple or dict, optional): Parameters for the query
        fetch_one (bool, optional): If True, fetch one result, otherwise fetch all

    Returns:
        list or dict: Query results or None if an error occurred
    """
    try:
        from sqlalchemy import text
        
        # Handle different parameter formats with proper SQLAlchemy syntax
        if params is None:
            result = db.session.execute(text(query))
        elif isinstance(params, (tuple, list)):
            # For positional parameters
            result = db.session.execute(text(query), params)
        elif isinstance(params, dict):
            result = db.session.execute(text(query), params)
        else:
            result = db.session.execute(text(query))
        
        if fetch_one:
            row = result.fetchone()
            return dict(row._mapping) if row else None
        else:
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows] if rows else []
            
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        db.session.rollback()
        return None

def get_latest_events(channel: str, since_timestamp=None, limit: int = 100):
    """Query the latest events for a given channel."""
    try:
        from common.events.models import EventModel
        query = db.session.query(EventModel).filter(EventModel.channel == channel)
        
        if since_timestamp:
            query = query.filter(EventModel.created_at > since_timestamp)
        
        events = query.order_by(EventModel.created_at.desc()).limit(limit).all()
        return [{"id": e.id, "event_type": e.event_type, "data": e.data, "created_at": e.created_at} for e in events]
    except Exception as e:
        logger.error(f"Failed to get latest events: {e}")
        return []

def check_database_connection():
    """
    Check if the database connection is working.

    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        result = execute_query("SELECT 1", fetch_one=True)
        return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
