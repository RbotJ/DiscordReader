"""
Event Consumer Utilities

Provides functions for retrieving and processing events from the database.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from flask import has_app_context

logger = logging.getLogger(__name__)


def get_events_by_channel(channel: str, since_timestamp=None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Query events for a given channel.
    
    Args:
        channel: Event channel to query
        since_timestamp: Optional timestamp to get events since
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    if not has_app_context():
        logger.warning("Cannot query events outside Flask application context")
        return []
    
    try:
        from sqlalchemy import text
        from common.db import db
        
        if since_timestamp:
            query = text("""
                SELECT * FROM events 
                WHERE channel = :channel AND timestamp > :since_timestamp
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            result = db.session.execute(query, {
                'channel': channel,
                'since_timestamp': since_timestamp,
                'limit': limit
            })
        else:
            query = text("""
                SELECT * FROM events 
                WHERE channel = :channel
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            result = db.session.execute(query, {
                'channel': channel,
                'limit': limit
            })
        
        events = []
        for row in result:
            events.append({
                'id': row.id if hasattr(row, 'id') else None,
                'event_type': row.event_type,
                'channel': row.channel,
                'payload': row.payload,
                'source': row.source,
                'correlation_id': row.correlation_id,
                'timestamp': row.timestamp,
                'created_at': row.created_at
            })
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to query events for channel {channel}: {e}")
        return []


def get_latest_events(since_timestamp=None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Query the latest events across all channels.
    
    Args:
        since_timestamp: Optional timestamp to get events since
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    if not has_app_context():
        logger.warning("Cannot query events outside Flask application context")
        return []
    
    try:
        from sqlalchemy import text
        from common.db import db
        
        if since_timestamp:
            query = text("""
                SELECT * FROM events 
                WHERE timestamp > :since_timestamp
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            result = db.session.execute(query, {
                'since_timestamp': since_timestamp,
                'limit': limit
            })
        else:
            query = text("""
                SELECT * FROM events 
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            result = db.session.execute(query, {
                'limit': limit
            })
        
        events = []
        for row in result:
            events.append({
                'id': row.id if hasattr(row, 'id') else None,
                'event_type': row.event_type,
                'channel': row.channel,
                'payload': row.payload,
                'source': row.source,
                'correlation_id': row.correlation_id,
                'timestamp': row.timestamp,
                'created_at': row.created_at
            })
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to query latest events: {e}")
        return []


def get_events_by_correlation_id(correlation_id: str) -> List[Dict[str, Any]]:
    """
    Query events by correlation ID for tracing related events.
    
    Args:
        correlation_id: Correlation ID to search for
        
    Returns:
        List of event dictionaries
    """
    if not has_app_context():
        logger.warning("Cannot query events outside Flask application context")
        return []
    
    try:
        from sqlalchemy import text
        from common.db import db
        
        query = text("""
            SELECT * FROM events 
            WHERE correlation_id = :correlation_id
            ORDER BY timestamp ASC
        """)
        
        result = db.session.execute(query, {
            'correlation_id': correlation_id
        })
        
        events = []
        for row in result:
            events.append({
                'id': row.id if hasattr(row, 'id') else None,
                'event_type': row.event_type,
                'channel': row.channel,
                'payload': row.payload,
                'source': row.source,
                'correlation_id': row.correlation_id,
                'timestamp': row.timestamp,
                'created_at': row.created_at
            })
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to query events for correlation ID {correlation_id}: {e}")
        return []


def poll_events(channels: List[str], since_timestamp=None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Poll for new events across multiple channels.
    
    Args:
        channels: List of channels to poll
        since_timestamp: Optional timestamp to get events since
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    if not has_app_context():
        logger.warning("Cannot poll events outside Flask application context")
        return []
    
    try:
        from sqlalchemy import text
        from common.db import db
        
        # Build IN clause for channels
        channel_placeholders = ','.join([f':channel_{i}' for i in range(len(channels))])
        channel_params = {f'channel_{i}': channel for i, channel in enumerate(channels)}
        
        if since_timestamp:
            query = text(f"""
                SELECT * FROM events 
                WHERE channel IN ({channel_placeholders}) AND timestamp > :since_timestamp
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            params = {**channel_params, 'since_timestamp': since_timestamp, 'limit': limit}
        else:
            query = text(f"""
                SELECT * FROM events 
                WHERE channel IN ({channel_placeholders})
                ORDER BY timestamp DESC 
                LIMIT :limit
            """)
            params = {**channel_params, 'limit': limit}
        
        result = db.session.execute(query, params)
        
        events = []
        for row in result:
            events.append({
                'id': row.id if hasattr(row, 'id') else None,
                'event_type': row.event_type,
                'channel': row.channel,
                'payload': row.payload,
                'source': row.source,
                'correlation_id': row.correlation_id,
                'timestamp': row.timestamp,
                'created_at': row.created_at
            })
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to poll events for channels {channels}: {e}")
        return []


def get_latest_event_id() -> Optional[int]:
    """
    Get the ID of the latest event for polling purposes.
    
    Returns:
        Latest event ID or None
    """
    if not has_app_context():
        return None
    
    try:
        from sqlalchemy import text
        from common.db import db
        
        query = text("SELECT MAX(id) as max_id FROM events")
        result = db.session.execute(query)
        row = result.fetchone()
        
        return row.max_id if row and row.max_id else None
        
    except Exception as e:
        logger.error(f"Failed to get latest event ID: {e}")
        return None


class EventConsumer:
    """
    Event consumer class for subscribing to and processing events.
    """
    
    def __init__(self, service_name: str, channels: List[str], poll_interval: int = 5):
        """Initialize event consumer."""
        self.service_name = service_name
        self.channels = channels
        self.poll_interval = poll_interval
        self.callbacks = {}
        self.running = False
        self.thread = None
        self.last_timestamp = None
        
    def subscribe(self, event_type: str, callback_func):
        """Subscribe to a specific event type."""
        self.callbacks[event_type] = callback_func
        logger.info(f"Subscribed to {event_type} events")
    
    def start(self):
        """Start the event consumer."""
        if self.running:
            return
        
        self.running = True
        self.last_timestamp = datetime.utcnow()
        self.thread = threading.Thread(target=self._poll_worker, daemon=True)
        self.thread.start()
        logger.info(f"Event consumer {self.service_name} started")
    
    def stop(self):
        """Stop the event consumer."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        logger.info(f"Event consumer {self.service_name} stopped")
    
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self.running
    
    def _poll_worker(self):
        """Background worker for polling events."""
        import time
        import threading
        
        while self.running:
            try:
                events = poll_events(self.channels, since_timestamp=self.last_timestamp)
                
                if events:
                    # Update timestamp for next poll
                    self.last_timestamp = max(event['timestamp'] for event in events)
                    
                    # Process each event
                    for event in events:
                        self._process_event(event)
                
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in event consumer polling: {e}")
                time.sleep(self.poll_interval)
    
    def _process_event(self, event: Dict[str, Any]):
        """Process a single event."""
        event_type = event.get('event_type')
        if event_type in self.callbacks:
            try:
                self.callbacks[event_type](event)
            except Exception as e:
                logger.error(f"Error processing {event_type} event: {e}")


def subscribe_to_events(channels: List[str], callback_func, poll_interval: int = 5):
    """
    Subscribe to events on specified channels with a callback function.
    
    Args:
        channels: List of channels to subscribe to
        callback_func: Function to call when new events are found
        poll_interval: Polling interval in seconds
    """
    import time
    import threading
    
    def poll_worker():
        last_timestamp = datetime.utcnow()
        
        while True:
            try:
                events = poll_events(channels, since_timestamp=last_timestamp)
                
                if events:
                    # Update timestamp for next poll
                    last_timestamp = max(event['timestamp'] for event in events)
                    
                    # Call the callback with new events
                    callback_func(events)
                
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error in event subscription polling: {e}")
                time.sleep(poll_interval)
    
    # Start polling in background thread
    thread = threading.Thread(target=poll_worker, daemon=True)
    thread.start()
    
    logger.info(f"Started event subscription for channels: {channels}")
    return thread