"""
PostgreSQL-based Event System

This module provides a database-backed event system that replaces Redis pub/sub
for feature-to-feature communication in the trading application.
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Union

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Set up logging
logger = logging.getLogger(__name__)

# Event channel definitions to replace Redis channels
class EventChannels:
    """
    Event channel definitions used throughout the application.
    All former Redis channels are now mapped to PostgreSQL table entries.
    """
    # Market data channels
    MARKET_PRICE_UPDATE = "market:price:update"
    MARKET_BARS_UPDATE = "market:bars:update"
    MARKET_OPTION_UPDATE = "market:option:update"
    
    # Setup channels
    SETUP_CREATED = "setup:created"
    SETUP_UPDATED = "setup:updated"
    SETUP_DETECTED = "setup:detected"
    
    # Signal channels
    SIGNAL_TRIGGERED = "signal:triggered"
    SIGNAL_UPDATED = "signal:updated"
    SIGNAL_CANCELLED = "signal:cancelled"
    
    # Trade channels
    TRADE_EXECUTED = "trade:executed"
    TRADE_UPDATED = "trade:updated"
    TRADE_CLOSED = "trade:closed"
    
    # Discord channels
    DISCORD_MESSAGE_RECEIVED = "discord:message:received"
    DISCORD_BATCH_CREATED = "discord:batch:created"

# Create SQLAlchemy models
Base = declarative_base()

# Maintain a price cache in memory for quick lookups
_price_cache = {}

class EventEntry(Base):
    """Event entry in the database"""
    __tablename__ = 'event_bus'
    
    id = Column(Integer, primary_key=True)
    channel = Column(String(100), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(Text, nullable=True)  # Using payload instead of event_data
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime, nullable=True)

# Global connection and thread state
_db_engine = None
_db_session = None
_listeners = {}
_message_counters = {'published': 0, 'processed': 0, 'errors': 0}
_running = False
_listener_thread = None
_lock = threading.Lock()
_last_health_check = None
_last_processed_id = 0

def initialize_events(db_url=None):
    """
    Initialize the event system with a database connection.
    
    Args:
        db_url: Optional database URL, defaults to DATABASE_URL env var
    """
    global _db_engine, _db_session
    
    if not db_url:
        db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        logger.error("No DATABASE_URL provided for event system")
        return False
    
    try:
        # Create database engine and session
        _db_engine = create_engine(db_url)
        Session = sessionmaker(bind=_db_engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(_db_engine)
        
        # Create a fresh session
        _db_session = Session()
        
        logger.info(f"Event system initialized with database at {db_url}")
        return True
    except Exception as e:
        logger.error(f"Error initializing event system: {e}")
        return False

def get_session():
    """
    Get a fresh database session to avoid transaction issues.
    
    Returns:
        SQLAlchemy session
    """
    global _db_engine
    
    if not _db_engine:
        logger.error("Event system not initialized")
        return None
    
    try:
        Session = sessionmaker(bind=_db_engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        return None

def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to a channel.
    
    Args:
        channel: The channel to publish to
        data: The event data (must be JSON serializable)
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _message_counters
    
    # Create a fresh session for each publish operation
    session = get_session()
    if not session:
        logger.error("Event system not initialized")
        return False
    
    try:
        # Ensure data has event_type
        event_type = data.get('event_type', 'generic')
        
        # Create event entry
        event = EventEntry(
            channel=channel,
            event_type=event_type,
            payload=json.dumps(data),
            created_at=datetime.utcnow()
        )
        
        # Add to database
        session.add(event)
        session.commit()
        
        # Update counter
        _message_counters['published'] += 1
        
        logger.debug(f"Published event to channel {channel}: {event_type}")
        
        # Close the session
        session.close()
        return True
    except Exception as e:
        logger.error(f"Error publishing event to {channel}: {e}")
        _message_counters['errors'] += 1
        
        # Try to rollback the transaction
        try:
            session.rollback()
        except:
            pass
        
        # Make sure to close the session
        try:
            session.close()
        except:
            pass
            
        return False

def subscribe(channels: List[str], callback: Callable) -> bool:
    """
    Subscribe to channels with a callback.
    
    Args:
        channels: List of channels to subscribe to
        callback: Function to call when an event is received
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _listeners, _lock
    
    if not _db_session:
        logger.error("Event system not initialized")
        return False
    
    try:
        with _lock:
            # Register callback for each channel
            for channel in channels:
                if channel not in _listeners:
                    _listeners[channel] = []
                if callback not in _listeners[channel]:
                    _listeners[channel].append(callback)
        
        # Start listener thread if not already running
        start_listener()
        
        logger.info(f"Subscribed to channels: {channels}")
        return True
    except Exception as e:
        logger.error(f"Error subscribing to channels {channels}: {e}")
        return False

def unsubscribe(channels: List[str], callback: Callable) -> bool:
    """
    Unsubscribe from channels.
    
    Args:
        channels: List of channels to unsubscribe from
        callback: Callback function to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _listeners, _lock
    
    try:
        with _lock:
            for channel in channels:
                if channel in _listeners and callback in _listeners[channel]:
                    _listeners[channel].remove(callback)
                    # Remove channel if no more listeners
                    if not _listeners[channel]:
                        del _listeners[channel]
        
        logger.info(f"Unsubscribed from channels: {channels}")
        return True
    except Exception as e:
        logger.error(f"Error unsubscribing from channels {channels}: {e}")
        return False

def unsubscribe_all() -> bool:
    """
    Unsubscribe from all channels.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global _listeners, _lock
    
    try:
        with _lock:
            _listeners.clear()
        
        logger.info("Unsubscribed from all channels")
        return True
    except Exception as e:
        logger.error(f"Error unsubscribing from all channels: {e}")
        return False

def start_listener():
    """Start the event listener thread if not already running."""
    global _running, _listener_thread
    
    if _running and _listener_thread and _listener_thread.is_alive():
        return
    
    _running = True
    _listener_thread = threading.Thread(target=_listen, daemon=True)
    _listener_thread.start()
    
    logger.info("Event listener thread started")

def stop_listener():
    """Stop the event listener thread."""
    global _running
    
    _running = False
    
    logger.info("Event listener thread stopping")

def _listen():
    """Background thread that listens for events"""
    global _running, _message_counters, _last_processed_id, _last_health_check
    
    logger.info("PostgreSQL event listener thread started")
    
    while _running:
        try:
            # Update health check timestamp
            _last_health_check = time.time()
            
            # Get unprocessed events from database
            events = _db_session.query(EventEntry) \
                .filter(EventEntry.processed == False) \
                .filter(EventEntry.id > _last_processed_id) \
                .order_by(EventEntry.id.asc()) \
                .limit(100) \
                .all()
            
            if not events:
                # No events to process, sleep briefly
                time.sleep(0.1)
                continue
            
            # Process each event
            for event in events:
                try:
                    # Parse JSON data
                    data = json.loads(event.payload)
                    
                    # Process event with registered callbacks
                    with _lock:
                        if event.channel in _listeners:
                            for callback in _listeners[event.channel]:
                                try:
                                    callback(event.channel, data)
                                except Exception as e:
                                    logger.error(f"Error in event callback: {e}")
                                    _message_counters['errors'] += 1
                    
                    # Mark event as processed
                    event.processed = True
                    event.processed_at = datetime.utcnow()
                    _db_session.commit()
                    
                    # Update counters
                    _message_counters['processed'] += 1
                    _last_processed_id = event.id
                    
                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}")
                    _message_counters['errors'] += 1
                    # Continue to next event
                    continue
            
        except Exception as e:
            logger.error(f"Error in event listener thread: {e}")
            time.sleep(1)  # Sleep to avoid tight loop on error
    
    logger.info("Event listener thread stopped")

def clear_events():
    """
    Clear all events from the database.
    
    Returns:
        int: Number of events cleared
    """
    if not _db_session:
        logger.error("Event system not initialized")
        return 0
    
    try:
        # Delete all events
        count = _db_session.query(EventEntry).delete()
        _db_session.commit()
        
        logger.info(f"Cleared {count} events from database")
        return count
    except Exception as e:
        logger.error(f"Error clearing events: {e}")
        return 0

def poll_events(channel: Union[str, List[str]], last_id: int = 0, count: int = 100) -> List[Dict[str, Any]]:
    """
    Poll for events from a channel since a given ID.
    
    Args:
        channel: The channel to poll from (string or list of strings)
        last_id: Only get events with ID greater than this
        count: Maximum number of events to return
        
    Returns:
        List of event data dictionaries
    """
    # Create a new session for this query to avoid transaction issues
    session = get_session()
    if not session:
        logger.error("Could not create database session for polling events")
        return []
    
    try:
        # Start with a base query for events newer than last_id
        query = session.query(EventEntry).filter(EventEntry.id > last_id)
        
        # Apply channel filter - handle both string and list inputs
        if isinstance(channel, list):
            if channel:  # Only if the list isn't empty
                # Get the channel strings from the list
                channel_strings = [c for c in channel if isinstance(c, str)]
                if channel_strings:
                    query = query.filter(EventEntry.channel.in_(channel_strings))
        elif isinstance(channel, str):
            query = query.filter(EventEntry.channel == channel)
        
        # Get events ordered by ID with limit
        events = query.order_by(EventEntry.id.asc()).limit(count).all()
        
        # Convert to list of data dictionaries
        result = []
        for event in events:
            try:
                # Convert JSON data to dictionary
                if event.payload:
                    data = json.loads(event.payload)
                    
                    # Add event metadata
                    data['_event_id'] = event.id
                    data['_event_timestamp'] = event.created_at.isoformat()
                    
                    result.append(data)
            except Exception as e:
                logger.error(f"Error parsing event payload for ID {event.id}: {e}")
        
        # Close the session
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error polling events from channel {channel}: {e}")
        # Make sure to close the session even on error
        session.close()
        return []

def get_latest_event_id(channel: Union[str, List[str]] = None) -> int:
    """
    Get the latest event ID for a channel, or across all channels.
    
    Args:
        channel: Optional channel filter (string or list of strings)
        
    Returns:
        Latest event ID, or 0 if no events found
    """
    # Create a new session for this query
    session = get_session()
    if not session:
        logger.error("Could not create database session for getting latest event ID")
        return 0
    
    try:
        # Create query for the latest event ID
        query = session.query(EventEntry.id)
        
        # Filter by channel if specified
        if channel:
            if isinstance(channel, list):
                if channel:  # Only if the list isn't empty
                    # Get the channel strings from the list
                    channel_strings = [c for c in channel if isinstance(c, str)]
                    if channel_strings:
                        query = query.filter(EventEntry.channel.in_(channel_strings))
            elif isinstance(channel, str):
                query = query.filter(EventEntry.channel == channel)
        
        # Get the max ID
        result = query.order_by(EventEntry.id.desc()).first()
        
        # Return the ID or 0 if no events
        result_id = result[0] if result else 0
        
        # Close the session
        session.close()
        return result_id
    except Exception as e:
        logger.error(f"Error getting latest event ID: {e}")
        # Make sure to close the session even on error
        try:
            session.close()
        except:
            pass
        return 0

# Price cache functions
def update_price_cache(ticker: str, price: float, timestamp: Optional[datetime] = None) -> bool:
    """
    Update the price in the cache.
    
    Args:
        ticker: The ticker symbol
        price: The current price
        timestamp: Optional timestamp, defaults to now
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _price_cache
    
    if not timestamp:
        timestamp = datetime.utcnow()
    
    _price_cache[ticker] = {
        'price': price,
        'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
    }
    
    # Also publish an event for subscribers
    try:
        event_data = {
            'event_type': 'price_update',
            'ticker': ticker,
            'price': price,
            'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
        }
        publish_event(EventChannels.MARKET_PRICE_UPDATE, event_data)
        return True
    except Exception as e:
        logger.error(f"Error publishing price update for {ticker}: {e}")
        return False

def get_price_from_cache(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get the price data from cache.
    
    Args:
        ticker: The ticker symbol
        
    Returns:
        Dict with price data or None if not found
    """
    global _price_cache
    
    if ticker in _price_cache:
        return _price_cache[ticker]
    return None

def clear_price_cache() -> bool:
    """
    Clear the price cache.
    
    Returns:
        bool: True if successful
    """
    global _price_cache
    
    _price_cache.clear()
    return True

def get_status() -> Dict[str, Any]:
    """
    Get the status of the event system.
    
    Returns:
        Dictionary with status information
    """
    return {
        'connected': _db_engine is not None,
        'running': _running,
        'last_check': datetime.now().isoformat(),
        'message_counts': _message_counters
    }
    """
    Get the status of the event system.
    
    Returns:
        dict: Status information
    """
    global _running, _message_counters, _last_health_check, _price_cache
    
    return {
        'running': _running,
        'listener_alive': _listener_thread.is_alive() if _listener_thread else False,
        'channels': list(_listeners.keys()),
        'published': _message_counters['published'],
        'processed': _message_counters['processed'],
        'errors': _message_counters['errors'],
        'last_health_check': datetime.fromtimestamp(_last_health_check).isoformat() if _last_health_check else None,
        'last_processed_id': _last_processed_id,
        'price_cache_size': len(_price_cache)
    }