"""
Ingestion Listener Module

Focused listener that only handles event listening and delegates processing to service.
Clean separation between listening and business logic.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from common.db import get_latest_events
from common.events.constants import EventChannels
from common.events.bus import get_event_bus

logger = logging.getLogger(__name__)


class IngestionListener:
    """
    Clean ingestion listener focused solely on event listening.
    Delegates all processing to the ingestion service.
    """
    
    def __init__(self, ingestion_service=None):
        """Initialize the ingestion listener."""
        self.ingestion_service = ingestion_service
        self.last_processed_event_id = None
        self.running = False
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'errors': 0,
            'last_activity': None
        }
    
    async def start_listening(self, poll_interval: float = 5.0):
        """Start listening for ingestion events using event bus subscription."""
        if not self.ingestion_service:
            logger.error("No ingestion service provided to listener")
            return
            
        self.running = True
        logger.info("Ingestion listener starting - subscribing to discord.message.new events")
        
        try:
            # Get event bus and subscribe to discord message events
            bus = await get_event_bus()
            bus.subscribe("discord.message.new", self._handle_discord_message_event)
            logger.info("Successfully subscribed to discord.message.new events")
            
            # Keep the listener alive with periodic stats updates
            while self.running:
                try:
                    self._update_stats()
                    await asyncio.sleep(poll_interval)
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping listener")
                    break
                except Exception as e:
                    logger.error(f"Error in listener main loop: {e}")
                    self.stats['errors'] += 1
                    await asyncio.sleep(poll_interval)
                    
        except Exception as e:
            logger.error(f"Error setting up event subscription: {e}")
            self.stats['errors'] += 1
    
    def stop_listening(self):
        """Stop the listener."""
        self.running = False
        logger.info("Ingestion listener stopped")
    
    async def _process_pending_events(self):
        """Process any pending events and delegate to service."""
        try:
            events = get_latest_events(
                EventChannels.DISCORD_MESSAGE,
                since_timestamp=self.last_processed_event_id,
                limit=10
            )
            
            if not events:
                return
            
            logger.debug(f"Received {len(events)} events")
            self.stats['events_received'] += len(events)
            
            for event in events:
                success = await self._handle_event(event)
                if success:
                    self.last_processed_event_id = event.get('id')
                    self.stats['events_processed'] += 1
                
        except Exception as e:
            logger.error(f"Error processing pending events: {e}")
            self.stats['errors'] += 1
    
    async def _handle_discord_message_event(self, event):
        """Handle discord.message.new events from the event bus."""
        try:
            logger.info(f"Received discord.message.new event: {event.data}")
            self.stats['events_received'] += 1
            
            # Extract channel_id from event data
            channel_id = event.data.get('channel_id')
            if not channel_id:
                logger.warning("No channel_id in discord message event")
                return False
            
            # Trigger ingestion for this channel
            if self.ingestion_service:
                success = await self.ingestion_service.handle_event({
                    'event_type': 'discord.message.new',
                    'payload': event.data
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

    async def _handle_event(self, event: Dict[str, Any]) -> bool:
        """Handle a single event by delegating to service."""
        try:
            # Simply pass the event to the service for processing
            # The service handles all business logic
            if self.ingestion_service:
                return await self.ingestion_service.handle_event(event)
            return False
            
        except Exception as e:
            logger.error(f"Error handling event: {e}")
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
        
        # Start listener in background task
        import asyncio
        asyncio.create_task(_global_listener.start_listening())
        logger.info("Ingestion listener started successfully")
        
    except Exception as e:
        logger.error(f"Error starting ingestion listener: {e}")


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