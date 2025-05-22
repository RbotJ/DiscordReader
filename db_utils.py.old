"""
Database Utilities

This module provides database utility functions for the trading application.
"""
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connection():
    """
    Get a connection to the PostgreSQL database.
    
    Returns:
        SQLAlchemy engine or None if connection failed
    """
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return None
    
    try:
        # Create engine and connect to the database
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def store_discord_message(message_data):
    """
    Store a Discord message in the PostgreSQL database.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    if not message_data:
        logger.error("No message data to store")
        return False
        
    # Extract message details
    message_id = message_data.get('id')
    content = message_data.get('content')
    timestamp_str = message_data.get('timestamp')
    
    if not message_id or not content or not timestamp_str:
        logger.error("Message missing required fields (id, content, or timestamp)")
        return False
    
    engine = get_database_connection()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Parse ISO timestamp to date
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00') if timestamp_str.endswith('Z') else timestamp_str)
            message_date = timestamp.date().isoformat()
            
            # Store message in setup_messages table
            query = text("""
                INSERT INTO setup_messages (id, date, raw_text, source, created_at)
                VALUES (:id, :date, :raw_text, 'discord', NOW())
                ON CONFLICT (id) DO UPDATE
                SET raw_text = :raw_text, date = :date
                RETURNING id
            """)
            
            result = conn.execute(query, {
                'id': message_id,
                'date': message_date,
                'raw_text': content
            })
            
            # Commit the transaction
            conn.commit()
            
            logger.info(f"Stored Discord message {message_id} in database")
            return True
            
    except Exception as e:
        logger.error(f"Error storing message in database: {e}")
        return False

def get_messages_from_database(limit=10):
    """
    Get recent messages from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of messages or empty list if none found
    """
    engine = get_database_connection()
    if not engine:
        return []
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, date, raw_text, source, created_at
                FROM setup_messages
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = conn.execute(query, {'limit': limit})
            messages = []
            
            for row in result:
                messages.append({
                    'id': row[0],
                    'date': row[1].isoformat() if row[1] else None,
                    'content': row[2],
                    'source': row[3],
                    'created_at': row[4].isoformat() if row[4] else None
                })
            
            return messages
            
    except Exception as e:
        logger.error(f"Error retrieving messages from database: {e}")
        return []

def get_latest_message_from_database():
    """
    Get the latest message from the database.
    
    Returns:
        Message dictionary or None if not found
    """
    messages = get_messages_from_database(limit=1)
    if messages:
        return messages[0]
    return None

def get_message_stats_from_database():
    """
    Get statistics about stored messages from the database.
    
    Returns:
        Dictionary containing message statistics
    """
    engine = get_database_connection()
    if not engine:
        return {'count': 0}
    
    try:
        with engine.connect() as conn:
            # Get count of messages
            count_query = text("SELECT COUNT(*) FROM setup_messages")
            count_result = conn.execute(count_query).scalar()
            
            # Get latest message
            latest_query = text("""
                SELECT id, date, raw_text, created_at
                FROM setup_messages
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            latest_result = conn.execute(latest_query).fetchone()
            
            stats = {
                'count': count_result,
                'latest_id': None,
                'latest_timestamp': None,
                'latest_date': None
            }
            
            if latest_result:
                stats['latest_id'] = latest_result[0]
                stats['latest_date'] = latest_result[1].isoformat() if latest_result[1] else None
                stats['latest_timestamp'] = latest_result[3].isoformat() if latest_result[3] else None
            
            return stats
            
    except Exception as e:
        logger.error(f"Error retrieving message stats from database: {e}")
        return {'count': 0}