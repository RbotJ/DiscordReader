"""
Event Publisher

This module handles publishing events to the system via the database
instead of using Redis. This allows for event-driven processing 
without Redis dependency.
"""
import os
import json
import logging
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Event types
class EventType:
    DISCORD_MESSAGE_RECEIVED = "discord.message.received"
    DISCORD_SETUP_MESSAGE_RECEIVED = "discord.setup.received"
    TICKER_PRICE_UPDATE = "ticker.price.update"
    SIGNAL_TRIGGERED = "signal.triggered"
    TRADE_EXECUTED = "trade.executed"
    POSITION_UPDATED = "position.updated"
    BIAS_FLIPPED = "bias.flipped"

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

def publish_event(event_type: str, data: Dict[str, Any], channel: str = "events") -> bool:
    """
    Publish an event to the event_bus table in the database.
    
    Args:
        event_type: Type of event (e.g., discord.message.received)
        data: Event data
        channel: Event channel/category
        
    Returns:
        True if successful, False otherwise
    """
    engine = get_database_connection()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Convert data to JSON
            json_data = json.dumps(data)
            
            # Current timestamp
            timestamp = datetime.now().isoformat()
            
            # Insert event into event_bus table
            query = text("""
                INSERT INTO event_bus (event_type, channel, payload, created_at)
                VALUES (:event_type, :channel, :payload, NOW())
                RETURNING id
            """)
            
            result = conn.execute(query, {
                'event_type': event_type,
                'channel': channel,
                'payload': json_data
            })
            
            # Commit the transaction
            conn.commit()
            
            # Get the event ID
            row = result.fetchone()
            if row:
                event_id = row[0]
                logger.debug(f"Published event {event_type} to {channel} with ID {event_id}")
                return True
            else:
                logger.error(f"Failed to publish event {event_type} to {channel}")
                return False
            
    except Exception as e:
        logger.error(f"Error publishing event to database: {e}")
        return False

def get_events(channel: str = "events", after_id: Optional[int] = None, limit: int = 100) -> list:
    """
    Get events from the event_bus table.
    
    Args:
        channel: Event channel/category
        after_id: Only get events after this ID
        limit: Maximum number of events to retrieve
        
    Returns:
        List of events or empty list if none found
    """
    engine = get_database_connection()
    if not engine:
        return []
    
    try:
        with engine.connect() as conn:
            if after_id:
                query = text("""
                    SELECT id, event_type, channel, payload, created_at
                    FROM event_bus
                    WHERE channel = :channel AND id > :after_id
                    ORDER BY id ASC
                    LIMIT :limit
                """)
                result = conn.execute(query, {
                    'channel': channel,
                    'after_id': after_id,
                    'limit': limit
                })
            else:
                query = text("""
                    SELECT id, event_type, channel, payload, created_at
                    FROM event_bus
                    WHERE channel = :channel
                    ORDER BY id ASC
                    LIMIT :limit
                """)
                result = conn.execute(query, {
                    'channel': channel,
                    'limit': limit
                })
            
            events = []
            for row in result:
                events.append({
                    'id': row[0],
                    'event_type': row[1],
                    'channel': row[2],
                    'data': json.loads(row[3]) if row[3] else {},
                    'created_at': row[4].isoformat() if row[4] else None
                })
            
            return events
            
    except Exception as e:
        logger.error(f"Error retrieving events from database: {e}")
        return []

def publish_discord_message(message_data: Dict[str, Any]) -> bool:
    """
    Publish a Discord message as an event.
    
    Args:
        message_data: Discord message data
        
    Returns:
        True if successful, False otherwise
    """
    # Extract message details
    message_id = message_data.get('id')
    
    if not message_id:
        logger.error("Cannot publish message without an ID")
        return False
    
    # Publish as an event
    return publish_event(
        event_type=EventType.DISCORD_MESSAGE_RECEIVED,
        data=message_data,
        channel="discord:messages"
    )

def publish_discord_setup(message_data: Dict[str, Any]) -> bool:
    """
    Publish a Discord setup message as an event.
    
    Args:
        message_data: Discord message data that contains a trading setup
        
    Returns:
        True if successful, False otherwise
    """
    # Extract message details
    message_id = message_data.get('id')
    
    if not message_id:
        logger.error("Cannot publish setup without a message ID")
        return False
    
    # Add a flag indicating this is a setup
    message_data['is_setup'] = True
    
    # Publish as an event
    return publish_event(
        event_type=EventType.DISCORD_SETUP_MESSAGE_RECEIVED,
        data=message_data,
        channel="discord:setups"
    )