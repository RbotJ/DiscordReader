"""
PostgreSQL LISTEN/NOTIFY Event System

Unified event publisher and listener using PostgreSQL NOTIFY/LISTEN
for real-time cross-feature communication.

IMPORTANT: This is the only approved mechanism for cross-slice events. 
All components must use publish_event() or listen_for_events() from this file.
No other event systems should be used in this codebase.
"""

import asyncio
import asyncpg
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

# Global connection pool for PostgreSQL LISTEN/NOTIFY
_connection_pool = None
_listener_connections = {}


async def get_connection_pool():
    """Get or create the PostgreSQL connection pool."""
    global _connection_pool
    if _connection_pool is None:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        
        _connection_pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("PostgreSQL connection pool created for event system")
    
    return _connection_pool


async def publish_event_async(
    event_type: str, 
    data: Dict[str, Any], 
    channel: str = "events", 
    source: str = None, 
    correlation_id: str = None
) -> bool:
    """
    Publish event using PostgreSQL NOTIFY with comprehensive error handling and recovery.
    
    Args:
        event_type: Type of event (e.g. 'discord.message.new')
        data: Event data (dict)
        channel: PostgreSQL channel name (default: 'events')
        source: Source service/module (e.g. 'discord_bot')
        correlation_id: UUID string for tracing related events
        
    Returns:
        bool: True if event published successfully, False otherwise
    """
    import asyncpg
    import os
    
    message_id = data.get('message_id', 'unknown')
    
    try:
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        logger.debug(f"[publisher] Publishing {event_type} for message {message_id}")
        
        # Create event payload
        event_payload = {
            'event_type': event_type,
            'data': data,
            'source': source or 'unknown',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Use direct asyncpg connection to avoid pool conflicts
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("No DATABASE_URL available for async event publishing")
            return False
        
        # Create a new connection for this operation
        conn = await asyncpg.connect(database_url)
        
        try:
            # Insert into events table for persistence
            await conn.execute("""
                INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, event_type, channel, json.dumps(data), source, correlation_id, datetime.utcnow())
            
            # Send NOTIFY for real-time listeners using string interpolation
            payload_str = json.dumps(event_payload)
            notify_sql = f"NOTIFY \"{channel}\", '{payload_str}'"
            await conn.execute(notify_sql)
            
            logger.info(f"📢 Published event: {event_type} on channel {channel} from {source}")
            return True
            
        finally:
            await conn.close()
        
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")
        return False


def publish_event(
    event_type: str, 
    data: dict, 
    channel: str = "events", 
    source: str = None, 
    correlation_id: str = None
) -> bool:
    """
    Synchronous wrapper for event publishing that works in Flask context.
    
    Args:
        event_type: Type of event (e.g. 'discord.message.new')
        data: Event data (dict)
        channel: PostgreSQL channel name (default: 'events')
        source: Source service/module (e.g. 'discord_bot')
        correlation_id: UUID string for tracing related events
        
    Returns:
        bool: True if event published successfully, False otherwise
    """
    try:
        # For synchronous Flask context, we'll use the database directly
        if has_app_context():
            from sqlalchemy import text
            from common.db import db
            
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            
            # Insert into events table
            db.session.execute(text("""
                INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
                VALUES (:event_type, :channel, :data, :source, :correlation_id, :created_at)
            """), {
                'event_type': event_type,
                'channel': channel,
                'data': data,
                'source': source or 'unknown',
                'correlation_id': correlation_id,
                'created_at': datetime.utcnow()
            })
            
            # Use PostgreSQL NOTIFY via raw SQL
            event_payload = {
                'event_type': event_type,
                'data': data,
                'source': source or 'unknown',
                'correlation_id': correlation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            db.session.execute(text(f"NOTIFY {channel}, :payload"), {
                'payload': json.dumps(event_payload)
            })
            
            db.session.commit()
            
            logger.info(f"Published PostgreSQL event: {event_type} on channel {channel} from {source}")
            return True
        else:
            # For async contexts, schedule the async version
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create task for async publishing
                asyncio.create_task(publish_event_async(event_type, data, channel, source, correlation_id))
                return True
            else:
                # Run async version
                return loop.run_until_complete(publish_event_async(event_type, data, channel, source, correlation_id))
        
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")
        try:
            if has_app_context():
                from common.db import db
                db.session.rollback()
        except:
            pass
        return False


async def listen_for_events(handler: Callable, channel: str = "events"):
    """
    Listen for PostgreSQL NOTIFY events and call handler for each event.
    
    Args:
        handler: Async function to handle events - handler(event_type, payload)
        channel: PostgreSQL channel to listen on (default: 'events')
    """
    global _listener_connections
    
    try:
        pool = await get_connection_pool()
        conn = await pool.acquire()
        _listener_connections[channel] = conn
        
        # Set up the listener
        await conn.add_listener(channel, lambda conn, pid, channel, payload: 
                               asyncio.create_task(_handle_notification(handler, payload)))
        
        logger.info(f"PostgreSQL listener started for channel: {channel}")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in PostgreSQL listener for channel {channel}: {e}")
        # Clean up connection
        if channel in _listener_connections:
            try:
                await _listener_connections[channel].close()
                del _listener_connections[channel]
            except:
                pass


async def _handle_notification(handler: Callable, payload: str):
    """Handle a PostgreSQL notification by calling the provided handler."""
    try:
        event_data = json.loads(payload)
        event_type = event_data.get('event_type')
        data = event_data.get('data', {})
        
        logger.info(f"Received PostgreSQL event: {event_type} from channel 'events'")
        
        # Call the handler
        if asyncio.iscoroutinefunction(handler):
            await handler(event_type, data)
        else:
            handler(event_type, data)
            
    except Exception as e:
        logger.error(f"Error handling PostgreSQL notification: {e}")


def publish_event_safe(
    event_type: str, 
    data: dict, 
    channel: str = "events", 
    source: str = None, 
    correlation_id: str = None
) -> bool:
    """
    Safe event publishing that works both inside and outside Flask context.
    Uses direct database connection when Flask context is not available.
    
    Args:
        event_type: Type of event
        data: Event data
        channel: Event channel
        source: Source service/module
        correlation_id: UUID string for tracing
        
    Returns:
        bool: True if published successfully
    """
    if has_app_context():
        return publish_event(event_type, data, channel, source, correlation_id)
    else:
        # Use direct database connection when Flask context not available
        return _publish_event_direct(event_type, data, channel, source, correlation_id)


def _publish_event_direct(
    event_type: str, 
    data: dict, 
    channel: str = "events", 
    source: str = None, 
    correlation_id: str = None
) -> bool:
    """
    Direct database event publishing without Flask context.
    """
    import os
    import psycopg2
    import json
    import uuid
    from datetime import datetime
    
    try:
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Create event payload
        event_payload = {
            'event_type': event_type,
            'data': data,
            'source': source or 'unknown',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Connect to database
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("No DATABASE_URL available for direct event publishing")
            return False
            
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Insert into events table
        cur.execute("""
            INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (event_type, channel, json.dumps(data), source, correlation_id, datetime.utcnow()))
        
        # Send PostgreSQL NOTIFY
        notify_payload = json.dumps(event_payload)
        cur.execute(f'NOTIFY "{channel}", %s', (notify_payload,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Event [{event_type}] published successfully via direct connection")
        return True
        
    except Exception as e:
        logger.error(f"Error in direct event publishing: {e}")
        return False


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