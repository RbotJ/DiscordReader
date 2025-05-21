"""
Event Bus System

This module provides event publishing and subscription functionality
using PostgreSQL instead of Redis.
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union

from app import db
from sqlalchemy import text

# Configure logging
logger = logging.getLogger(__name__)

# Define standard event channels (keeping same names as before for compatibility)
class EventChannels:
    """Standard event channels used throughout the application."""
    SETUP_RECEIVED = "setup.received"
    SETUP_PARSED = "setup.parsed"
    MARKET_PRICE_UPDATE = "market.price_update"
    SIGNAL_TRIGGERED = "signal.triggered"
    TRADE_EXECUTED = "trade.executed"
    POSITION_UPDATED = "position.updated"
    POSITION_CLOSED = "position.closed"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

# Discord-specific channels
DISCORD_RAW_MESSAGE_CHANNEL = "events:discord:raw_messages"
DISCORD_SETUP_MESSAGE_CHANNEL = "events:discord:setup_messages"
SETUP_CREATED_CHANNEL = "events:setup:created"
SIGNAL_CREATED_CHANNEL = "events:signal:created"

def publish_event(channel: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Publish an event to the event bus.
    
    Args:
        channel: The channel to publish to
        event_type: The type of event
        payload: The event data payload
        
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        # Add timestamp if not present
        if 'timestamp' not in payload:
            payload['timestamp'] = datetime.now().isoformat()
            
        with db.session.begin():
            # Insert into event_bus table
            sql = text("""
                INSERT INTO event_bus (event_type, channel, payload)
                VALUES (:event_type, :channel, :payload)
            """)
            
            db.session.execute(
                sql, 
                {
                    'event_type': event_type,
                    'channel': channel,
                    'payload': json.dumps(payload)
                }
            )
            
        logger.debug(f"Published event to {channel}: {event_type}")
        return True
        
    except Exception as e:
        logger.error(f"Error publishing event to {channel}: {e}")
        return False

def poll_events(channels: List[str], since_id: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Poll for new events on the specified channels.
    
    Args:
        channels: List of channels to poll
        since_id: Get events with ID greater than this
        limit: Maximum number of events to return
        
    Returns:
        List of events
    """
    try:
        with db.session.begin():
            sql = text("""
                SELECT id, event_type, channel, payload, created_at
                FROM event_bus
                WHERE channel = ANY(:channels)
                AND id > :since_id
                ORDER BY id ASC
                LIMIT :limit
            """)
            
            result = db.session.execute(
                sql, 
                {
                    'channels': channels,
                    'since_id': since_id,
                    'limit': limit
                }
            )
            
            events = []
            for row in result:
                events.append({
                    'id': row.id,
                    'event_type': row.event_type,
                    'channel': row.channel,
                    'payload': json.loads(row.payload) if row.payload else {},
                    'created_at': row.created_at.isoformat() if row.created_at else None
                })
                
            return events
            
    except Exception as e:
        logger.error(f"Error polling events: {e}")
        return []

def get_latest_event_id() -> int:
    """
    Get the latest event ID from the event bus.
    
    Returns:
        The latest event ID or 0 if no events exist
    """
    try:
        with db.session.begin():
            sql = text("SELECT MAX(id) FROM event_bus")
            result = db.session.execute(sql).scalar()
            return result or 0
            
    except Exception as e:
        logger.error(f"Error getting latest event ID: {e}")
        return 0

# Event listener class for background polling
class EventListener:
    """Event listener that polls the event bus in a background thread."""
    
    def __init__(self, channels: List[str], callback: Callable[[Dict[str, Any]], None], 
                 poll_interval: float = 0.5):
        """
        Initialize an event listener.
        
        Args:
            channels: List of channels to subscribe to
            callback: Function to call when an event is received
            poll_interval: How often to poll for events (in seconds)
        """
        self.channels = channels
        self.callback = callback
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
        self.last_id = get_latest_event_id()
        
    def start(self) -> bool:
        """
        Start the event listener thread.
        
        Returns:
            bool: True if started, False otherwise
        """
        if self.running:
            logger.warning("Event listener already running")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Started event listener for channels: {self.channels}")
        return True
        
    def stop(self) -> bool:
        """
        Stop the event listener thread.
        
        Returns:
            bool: True if stopped, False otherwise
        """
        if not self.running:
            logger.warning("Event listener not running")
            return False
            
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning("Event listener thread did not terminate cleanly")
            self.thread = None
            
        logger.info("Stopped event listener")
        return True
        
    def _poll_loop(self):
        """Poll for events in a loop."""
        logger.info("Event listener thread started")
        
        while self.running:
            try:
                # Poll for new events
                events = poll_events(self.channels, self.last_id)
                
                # Process events
                for event in events:
                    try:
                        # Update last_id
                        self.last_id = max(self.last_id, event['id'])
                        
                        # Call callback
                        self.callback(event)
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
                
                # Sleep briefly
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                time.sleep(1.0)  # Sleep longer on error

# For backward compatibility
def subscribe_to_channel(channel: str, callback: Callable) -> EventListener:
    """
    Subscribe to a channel.
    
    Args:
        channel: Channel to subscribe to
        callback: Function to call when an event is received
        
    Returns:
        EventListener instance
    """
    listener = EventListener([channel], callback)
    listener.start()
    return listener

# Cache operations for price updates
def update_price_cache(symbol: str, price: float) -> bool:
    """
    Update the price cache for a symbol.
    
    Args:
        symbol: The ticker symbol
        price: The current price
        
    Returns:
        bool: True if updated, False otherwise
    """
    try:
        with db.session.begin():
            sql = text("""
                INSERT INTO price_cache (symbol, last_price, updated_at)
                VALUES (:symbol, :price, NOW())
                ON CONFLICT (symbol) 
                DO UPDATE SET 
                    last_price = :price,
                    updated_at = NOW()
            """)
            
            db.session.execute(
                sql, 
                {
                    'symbol': symbol,
                    'price': price
                }
            )
            
        return True
        
    except Exception as e:
        logger.error(f"Error updating price cache for {symbol}: {e}")
        return False

def get_price_from_cache(symbol: str) -> Optional[float]:
    """
    Get the cached price for a symbol.
    
    Args:
        symbol: The ticker symbol
        
    Returns:
        The cached price or None if not found
    """
    try:
        with db.session.begin():
            sql = text("""
                SELECT last_price FROM price_cache
                WHERE symbol = :symbol
            """)
            
            result = db.session.execute(sql, {'symbol': symbol}).scalar()
            return result
            
    except Exception as e:
        logger.error(f"Error getting price from cache for {symbol}: {e}")
        return None

def clear_price_cache(symbol: Optional[str] = None) -> bool:
    """
    Clear the price cache for a symbol or all symbols.
    
    Args:
        symbol: Symbol to clear or None to clear all
        
    Returns:
        bool: True if cleared, False otherwise
    """
    try:
        with db.session.begin():
            if symbol:
                sql = text("DELETE FROM price_cache WHERE symbol = :symbol")
                db.session.execute(sql, {'symbol': symbol})
            else:
                sql = text("DELETE FROM price_cache")
                db.session.execute(sql)
                
        return True
        
    except Exception as e:
        logger.error(f"Error clearing price cache: {e}")
        return False