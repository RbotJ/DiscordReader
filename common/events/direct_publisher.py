"""
Direct Event Publishing for Discord Bot

Provides direct database event publishing bypassing Flask context.
Used by Discord bot running in separate async context.
"""

import os
import psycopg2
import json
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def publish_event_direct(event_type: str, channel: str, payload: dict, source: str = "unknown"):
    """
    ⚠️ FALLBACK/DIAGNOSTIC ONLY - Direct database event publishing bypassing event bus.
    This bypasses the intended PostgreSQL event architecture and should only be used
    for testing or emergency fallback scenarios.
    
    Args:
        event_type: Type of event (e.g. 'discord.message.new')
        channel: Event channel (e.g. 'events')
        payload: Event data dictionary
        source: Source service/module (e.g. 'discord_bot')
        
    Returns:
        str: Event ID if successful, None if failed
    """
    logger.warning(f"⚠️ EVENT BUS BYPASSED: Using direct publishing for {event_type} from {source}")
    logger.warning(f"⚠️ This indicates event bus failure - investigate async publishing issues")
    print(f"📤 FALLBACK: Publishing event with payload: {payload}")
    logger.info(f"📤 Starting direct event publishing: {event_type}")
    
    try:
        # Generate proper UUID correlation ID 
        correlation_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        logger.info(f"Generated correlation_id: {correlation_id}")
        
        # Connect to database
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("No DATABASE_URL available for direct event publishing")
            return None
            
        logger.info("Connecting to database for direct event publishing")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Serialize payload as JSON string for Text column
        data_json = json.dumps(payload)
        logger.info(f"Serialized payload length: {len(data_json)}")
        
        # Insert into events table
        logger.info("Executing INSERT into events table")
        cur.execute("""
            INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (event_type, channel, data_json, source, correlation_id, current_time))
        
        event_id = cur.fetchone()[0]
        logger.info(f"Event inserted with ID: {event_id}")
        
        # Send PostgreSQL NOTIFY
        notify_payload = json.dumps({
            'event_type': event_type,
            'data': payload,
            'source': source,
            'correlation_id': correlation_id,
            'timestamp': current_time.isoformat()
        })
        
        logger.info("Sending PostgreSQL NOTIFY")
        cur.execute(f'NOTIFY "{channel}", %s', (notify_payload,))
        
        # Commit transaction
        logger.info("Committing transaction")
        conn.commit()
        
        # Close connection
        cur.close()
        conn.close()
        logger.info("Database connection closed")
        
        logger.info(f"[{source}] Published event {event_type} directly: {event_id}")
        return str(event_id)
        
    except Exception as e:
        logger.exception(f"Error in direct event publishing: {e}")
        try:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
        except:
            pass
        return None