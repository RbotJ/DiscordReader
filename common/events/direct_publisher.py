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
    Direct database event publishing bypassing Flask context.
    Used by Discord bot running in separate async context.
    
    Args:
        event_type: Type of event (e.g. 'discord.message.new')
        channel: Event channel (e.g. 'events')
        payload: Event data dictionary
        source: Source service/module (e.g. 'discord_bot')
        
    Returns:
        str: Event ID if successful, None if failed
    """
    try:
        # Generate correlation ID from message ID or create new one
        correlation_id = payload.get("message_id", str(uuid.uuid4()))
        
        # Connect to database
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("No DATABASE_URL available for direct event publishing")
            return None
            
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Insert into events table
        cur.execute("""
            INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (event_type, channel, json.dumps(payload), source, correlation_id, datetime.utcnow()))
        
        event_id = cur.fetchone()[0]
        
        # Send PostgreSQL NOTIFY
        notify_payload = json.dumps({
            'event_type': event_type,
            'data': payload,
            'source': source,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        cur.execute(f'NOTIFY "{channel}", %s', (notify_payload,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"[{source}] Published event {event_type} directly: {event_id}")
        return str(event_id)
        
    except Exception as e:
        logger.error(f"Error in direct event publishing: {e}")
        return None