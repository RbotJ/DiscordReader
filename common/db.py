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
    Publish event to the database using enhanced events schema with correlation tracking.
    
    Args:
        event_type: Type of event (e.g. 'setup.parsed')
        payload: Event data payload
        channel: Event channel (e.g. 'setup:created')
        source: Source service/module (e.g. 'discord_parser')
        correlation_id: UUID for tracing related events
    """
    try:
        from features.events.enhanced_publisher import EventPublisher
        event = EventPublisher.publish_event(
            channel=channel,
            event_type=event_type,
            data=payload,
            source=source,
            correlation_id=correlation_id
        )
        return event is not None
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        return False

def execute_query(query, params=None, fetch_one=False):
    """
    Execute a raw SQL query safely.

    Args:
        query (str): SQL query to execute
        params (dict, optional): Parameters for the query
        fetch_one (bool, optional): If True, fetch one result, otherwise fetch all

    Returns:
        list or dict: Query results or None if an error occurred
    """
    try:
        sql_text = text(query)
        result = db.session.execute(sql_text, params or {})
        return result.fetchone() if fetch_one else result.fetchall()
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
