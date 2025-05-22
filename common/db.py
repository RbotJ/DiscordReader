"""
Database Utilities

A module providing a shared SQLAlchemy database instance and common database operations.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create a SQLAlchemy instance
db = SQLAlchemy()

def initialize_db(app):
    """Initialize database with app context"""
    try:
        db.init_app(app)
        with app.app_context():
            db.create_all()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def publish_event(event_type: str, payload: dict):
    """Publish event to database"""
    from common.models import Event
    try:
        event = Event(
            type=event_type,
            payload=payload,
            created_at=datetime.utcnow()
        )
        db.session.add(event)
        db.session.commit()
        return True
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
        from sqlalchemy import text
        
        # Create SQLAlchemy text object
        sql_text = text(query)
        
        # Execute the query
        result = db.session.execute(sql_text, params or {})
        
        # Fetch results
        if fetch_one:
            return result.fetchone()
        else:
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        db.session.rollback()
        return None

def check_database_connection():
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        # Simple query to test connection
        result = execute_query("SELECT 1", fetch_one=True)
        return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False