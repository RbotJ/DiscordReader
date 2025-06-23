"""
Ingestion Listener Module

PostgreSQL LISTEN/NOTIFY based listener for cross-feature communication.
Clean separation between listening and business logic.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from common.events.publisher import listen_for_events

logger = logging.getLogger(__name__)


class IngestionListener:
    """
    PostgreSQL LISTEN/NOTIFY based ingestion listener.
    Delegates all processing to the ingestion service.
    """
    
    def __init__(self, ingestion_service=None):
        """Initialize the ingestion listener."""
        self.ingestion_service = ingestion_service
        self.running = False
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'errors': 0,
            'last_activity': None
        }
    
    async def start_listening(self, poll_interval: float = 5.0):
        """Start listening for ingestion events using PostgreSQL LISTEN/NOTIFY."""
        if not self.ingestion_service:
            logger.error("No ingestion service provided to listener")
            return
            
        self.running = True
        logger.info("Ingestion listener starting - subscribing to PostgreSQL events channel")
        
        try:
            # Start PostgreSQL LISTEN/NOTIFY listener
            await listen_for_events(self._handle_event, "events")
            
        except Exception as e:
            logger.error(f"Error setting up PostgreSQL listener: {e}")
            self.stats['errors'] += 1
    
    def stop_listening(self):
        """Stop the listener."""
        self.running = False
        logger.info("Ingestion listener stopped")

    async def _handle_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Handle PostgreSQL NOTIFY events."""
        try:
            logger.info("[listener] Received event: %s with payload ID: %s", event_type, data.get('message_id'))
            self.stats['events_received'] += 1
            self._update_stats()
            
            # Handle discord.message.new events
            if event_type == "discord.message.new":
                return await self._handle_discord_message_event(event_type, data)
            else:
                logger.debug(f"Unhandled event type: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")
            self.stats['errors'] += 1
            return False

    async def _handle_discord_message_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Handle discord.message.new events from PostgreSQL NOTIFY."""
        try:
            # Extract channel_id from event data
            channel_id = data.get('channel_id')
            if not channel_id:
                logger.warning("No channel_id in discord message event")
                self.stats['errors'] += 1
                return False
            
            # Trigger ingestion for this channel
            if self.ingestion_service:
                success = await self.ingestion_service.handle_event({
                    'event_type': event_type,
                    'payload': data
                })
                if success:
                    self.stats['events_processed'] += 1
                return success
            else:
                logger.error("No ingestion service available")
                return False
                
        except Exception as e:
            logger.error(f"Error handling discord message event: {e}")
            self.stats['errors'] += 1
            return False
    
    def _update_stats(self):
        """Update listener statistics."""
        self.stats['last_activity'] = datetime.utcnow()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current listener statistics."""
        return self.stats.copy()


# Global listener instance
_global_listener = None


async def start_ingestion_listener():
    """Start the global ingestion listener with proper service injection."""
    global _global_listener
    
    if _global_listener and _global_listener.running:
        logger.info("Ingestion listener already running")
        return
    
    # Import here to avoid circular imports
    from features.ingestion.service import get_ingestion_service
    
    try:
        # Create listener with injected service
        ingestion_service = get_ingestion_service()
        _global_listener = IngestionListener(ingestion_service=ingestion_service)
        
        # Start listener directly (await, don't create task)
        logger.info("Starting PostgreSQL ingestion listener...")
        await _global_listener.start_listening()
        
    except Exception as e:
        logger.error(f"Error starting ingestion listener: {e}")
        logger.exception("Full ingestion listener startup traceback:")


def stop_ingestion_listener():
    """Stop the global ingestion listener."""
    global _global_listener
    
    if _global_listener:
        _global_listener.stop_listening()
        _global_listener = None
        logger.info("Ingestion listener stopped")


def get_listener_stats() -> Dict[str, Any]:
    """Get statistics from the global listener."""
    global _global_listener
    
    if _global_listener:
        return _global_listener.get_stats()
    else:
        return {'status': 'not_running'}