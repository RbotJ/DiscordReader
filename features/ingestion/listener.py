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
        """Start listening for ingestion events with configurable polling."""
        if not self.ingestion_service:
            logger.error("No ingestion service provided to listener")
            return
            
        self.running = True
        logger.info(f"Ingestion listener started with {poll_interval}s poll interval")
        
        while self.running:
            try:
                await self._process_pending_events()
                self._update_stats()
                await asyncio.sleep(poll_interval)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping listener")
                break
            except Exception as e:
                logger.error(f"Error in listener main loop: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(poll_interval)
    
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
    
    async def _handle_event(self, event: Dict[str, Any]) -> bool:
        """Handle a single event by delegating to service."""
        try:
            # Simply pass the event to the service for processing
            # The service handles all business logic
            return await self.ingestion_service.handle_event(event)
            
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