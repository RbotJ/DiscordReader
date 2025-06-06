"""
Database Utilities

A module providing a shared SQLAlchemy database instance and common database operations.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
from sqlalchemy import text
import uuid
import json
from flask import has_app_context

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

# NOTE: publish_event has been moved to common/events/publisher.py
# Import from there instead: from common.events.publisher import publish_event

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
        result = db.session.execute(text(query), params or {})
        
        if query.strip().upper().startswith('SELECT'):
            if fetch_one:
                row = result.fetchone()
                return dict(row._mapping) if row else None
            else:
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        else:
            db.session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        db.session.rollback()
        return None

def get_latest_events(channel: str, since_timestamp=None, limit: int = 100):
    """Query the latest events for a given channel."""
    try:
        if since_timestamp:
            query = text("""
                SELECT * FROM events 
                WHERE channel = :channel AND timestamp > :since_timestamp
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            params = {'channel': channel, 'since_timestamp': since_timestamp, 'limit': limit}
        else:
            query = text("""
                SELECT * FROM events 
                WHERE channel = :channel 
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            params = {'channel': channel, 'limit': limit}
        
        result = db.session.execute(query, params)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
        
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
        # Simple query to test connection
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False