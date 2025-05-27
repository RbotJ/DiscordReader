
"""
Parsing Event Listener Module

Listens for MESSAGE_STORED events and triggers parsing workflow.
This module handles the event-driven parsing of Discord messages,
orchestrating the parse → store → emit SETUP_PARSED workflow.
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .parser import parse_setup_from_text
from .store import SetupStorageService
from features.ingestion.models import DiscordMessageModel
from common.db import db
from common.event_constants import EventChannels, EventType
from common.events import publish_event

logger = logging.getLogger(__name__)


class MessageStoredListener:
    """
    PostgreSQL LISTEN handler for MESSAGE_STORED events.
    
    This class listens for MESSAGE_STORED notifications from PostgreSQL
    and triggers the parsing workflow for new Discord messages.
    """
    
    def __init__(self):
        """Initialize the listener with required components."""
        self.storage_service = SetupStorageService()
        self.is_running = False
        self.connection = None
        self.stats = {
            'messages_processed': 0,
            'setups_parsed': 0,
            'errors': 0,
            'started_at': None
        }
    
    async def start_listening(self) -> None:
        """
        Start listening for MESSAGE_STORED events via PostgreSQL LISTEN.
        
        This method establishes a PostgreSQL connection and listens for
        NOTIFY events on the MESSAGE_STORED channel.
        """
        logger.info("Starting MESSAGE_STORED listener")
        self.is_running = True
        self.stats['started_at'] = datetime.utcnow()
        
        try:
            # Get database URL from SQLAlchemy
            database_url = str(db.engine.url)
            
            # Create dedicated connection for LISTEN
            self.connection = psycopg2.connect(database_url)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            cursor = self.connection.cursor()
            cursor.execute("LISTEN message_stored;")
            
            logger.info("PostgreSQL LISTEN established for message_stored channel")
            
            while self.is_running:
                # Wait for notifications with timeout
                if self.connection.poll() == psycopg2.extensions.POLL_OK:
                    while self.connection.notifies:
                        notify = self.connection.notifies.pop(0)
                        await self._handle_notification(notify)
                
                # Brief sleep to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in MESSAGE_STORED listener: {e}")
            self.stats['errors'] += 1
            raise
        finally:
            if self.connection:
                self.connection.close()
    
    def stop_listening(self) -> None:
        """Stop the event listener."""
        logger.info("Stopping MESSAGE_STORED listener")
        self.is_running = False
    
    async def _handle_notification(self, notify) -> None:
        """
        Handle a PostgreSQL NOTIFY for MESSAGE_STORED.
        
        Args:
            notify: PostgreSQL notification object
        """
        try:
            # Parse notification payload
            if notify.payload:
                payload = json.loads(notify.payload)
            else:
                payload = {}
            
            message_id = payload.get('message_id')
            if not message_id:
                logger.warning("MESSAGE_STORED notification missing message_id")
                return
            
            # Get the stored message from database
            message = DiscordMessageModel.query.filter_by(
                message_id=message_id
            ).first()
            
            if not message:
                logger.warning(f"Message {message_id} not found in database")
                return
            
            # Skip if already processed
            if hasattr(message, 'is_processed') and message.is_processed:
                logger.debug(f"Message {message_id} already processed, skipping")
                return
            
            # Process the message
            await self._process_message(message)
            
            # Mark message as processed if the model supports it
            if hasattr(message, 'mark_as_processed'):
                message.mark_as_processed()
                db.session.commit()
            
            self.stats['messages_processed'] += 1
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing notification payload: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            logger.error(f"Error handling MESSAGE_STORED notification: {e}")
            self.stats['errors'] += 1
    
    async def _process_message(self, message: DiscordMessageModel) -> None:
        """
        Process a Discord message through the parsing pipeline.
        
        Args:
            message: DiscordMessageModel to process
        """
        try:
            logger.debug(f"Processing message {message.message_id} for parsing")
            
            # Parse message content for trading setups
            setup = parse_setup_from_text(message.content)
            
            if not setup:
                logger.debug(f"No setup found in message {message.message_id}")
                return
            
            # Store the setup
            try:
                stored_setup = self.storage_service.store_setup(setup)
                if stored_setup:
                    self.stats['setups_parsed'] += 1
                    
                    # Emit SETUP_PARSED event
                    await self._emit_setup_parsed_event(stored_setup, message)
                    
                    logger.info(f"Successfully parsed and stored setup from message {message.message_id}")
                else:
                    logger.warning(f"Failed to store setup from message {message.message_id}")
                    
            except Exception as e:
                logger.error(f"Error storing setup from message {message.message_id}: {e}")
                self.stats['errors'] += 1
            
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}")
            self.stats['errors'] += 1
    
    async def _emit_setup_parsed_event(self, setup, message: DiscordMessageModel) -> None:
        """
        Emit SETUP_PARSED event for a successfully parsed setup.
        
        Args:
            setup: SetupModel that was parsed and stored
            message: Original DiscordMessageModel
        """
        try:
            event_payload = {
                'setup_id': setup.id,
                'ticker': setup.ticker,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'confidence': setup.confidence,
                'source_message_id': message.message_id,
                'channel_id': getattr(message, 'channel_id', None),
                'parsed_at': datetime.utcnow().isoformat()
            }
            
            # Publish SETUP_PARSED event
            publish_event(
                event_type=EventType.SETUP_PARSED,
                channel=EventChannels.SETUP_CREATED,
                data=event_payload
            )
            
            logger.debug(f"Emitted SETUP_PARSED event for setup {setup.id}")
            
        except Exception as e:
            logger.error(f"Error emitting SETUP_PARSED event: {e}")
    
    def get_listener_stats(self) -> Dict[str, Any]:
        """
        Get listener statistics.
        
        Returns:
            Dict[str, Any]: Listener performance statistics
        """
        return {
            'is_running': self.is_running,
            'statistics': self.stats.copy(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def reset_stats(self) -> None:
        """Reset listener statistics."""
        self.stats = {
            'messages_processed': 0,
            'setups_parsed': 0,
            'errors': 0,
            'started_at': self.stats.get('started_at')
        }


# Global listener instance
_listener_instance = None


async def start_message_stored_listener() -> MessageStoredListener:
    """
    Start the MESSAGE_STORED listener.
    
    Returns:
        MessageStoredListener: Started listener instance
    """
    global _listener_instance
    
    if _listener_instance and _listener_instance.is_running:
        logger.warning("MESSAGE_STORED listener already running")
        return _listener_instance
    
    _listener_instance = MessageStoredListener()
    
    # Start listener in background task
    asyncio.create_task(_listener_instance.start_listening())
    
    return _listener_instance


def stop_message_stored_listener() -> None:
    """Stop the MESSAGE_STORED listener if running."""
    global _listener_instance
    
    if _listener_instance:
        _listener_instance.stop_listening()


def get_listener_stats() -> Optional[Dict[str, Any]]:
    """
    Get current listener statistics.
    
    Returns:
        Optional[Dict[str, Any]]: Listener stats or None if not running
    """
    global _listener_instance
    
    if _listener_instance:
        return _listener_instance.get_listener_stats()
    
    return None


async def process_single_message(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to process a single message for parsing.
    
    Args:
        message_id: Discord message ID to process
        
    Returns:
        Optional[Dict[str, Any]]: Processing results or None if failed
    """
    try:
        # Get message from database
        message = DiscordMessageModel.query.filter_by(
            message_id=message_id
        ).first()
        
        if not message:
            logger.warning(f"Message {message_id} not found")
            return None
        
        # Create temporary listener for processing
        temp_listener = MessageStoredListener()
        await temp_listener._process_message(message)
        
        return temp_listener.get_listener_stats()
        
    except Exception as e:
        logger.error(f"Error processing single message {message_id}: {e}")
        return None
