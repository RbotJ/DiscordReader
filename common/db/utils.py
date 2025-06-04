"""
Database Utilities

Common database utility functions for query execution, health checks, and data operations.
"""

import logging
from sqlalchemy import text
from .session import db

# Setup logging
logger = logging.getLogger(__name__)

def execute_query(query, params=None, fetch_one=False):
    """
    Execute a raw SQL query safely.

    Args:
        query (str): SQL query to execute
        params (tuple, list, or dict, optional): Parameters for the query
        fetch_one (bool, optional): If True, fetch one result, otherwise fetch all

    Returns:
        list or dict: Query results or None if an error occurred
    """
    try:
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

def check_database_connection():
    """
    Check if the database connection is working.

    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        result = execute_query("SELECT 1", fetch_one=True)
        if result and len(result) > 0:
            # Get the first value from the result dict
            first_value = list(result.values())[0]
            return first_value == 1
        return False
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def get_latest_events(channel: str, since_timestamp=None, limit: int = 100):
    """
    Query the latest events for a given channel.
    
    Args:
        channel (str): Event channel to query
        since_timestamp (datetime, optional): Get events since this timestamp
        limit (int): Maximum number of events to return
        
    Returns:
        list: List of event dictionaries
    """
    try:
        from common.events.models import Event
        query = db.session.query(Event).filter(Event.channel == channel)
        
        if since_timestamp:
            query = query.filter(Event.created_at > since_timestamp)
        
        events = query.order_by(Event.created_at.desc()).limit(limit).all()
        return [
            {
                "id": e.id, 
                "event_type": e.event_type, 
                "data": e.data, 
                "created_at": e.created_at,
                "source": e.source,
                "correlation_id": e.correlation_id
            } 
            for e in events
        ]
    except Exception as e:
        logger.error(f"Failed to get latest events: {e}")
        return []

def execute_bulk_insert(table_name: str, data_list: list):
    """
    Execute bulk insert operation.
    
    Args:
        table_name (str): Name of the table
        data_list (list): List of dictionaries with data to insert
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not data_list:
            return True
            
        # Build bulk insert query
        if data_list:
            columns = list(data_list[0].keys())
            placeholders = ', '.join([f':{col}' for col in columns])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            db.session.execute(text(query), data_list)
            db.session.commit()
            logger.debug(f"Bulk inserted {len(data_list)} records into {table_name}")
            return True
            
    except Exception as e:
        logger.error(f"Bulk insert failed for {table_name}: {e}")
        db.session.rollback()
        return False

def table_exists(table_name: str):
    """
    Check if a table exists in the database.
    
    Args:
        table_name (str): Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        result = execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name",
            {"table_name": table_name},
            fetch_one=True
        )
        return result is not None
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {e}")
        return False