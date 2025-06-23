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
        """Handle discord.message.new events from PostgreSQL NOTIFY with Flask context."""
        message_id = data.get('message_id', 'unknown')
        
        try:
            logger.info(f"[listener] Processing Discord event for message: {message_id}")
            
            # Extract channel_id from event data
            channel_id = data.get('channel_id')
            if not channel_id:
                logger.warning(f"[listener] No channel_id in discord message event for {message_id}")
                self.stats['errors'] += 1
                return False
            
            # Verify we have ingestion service
            if not self.ingestion_service:
                logger.error(f"[listener] No ingestion service available for {message_id}")
                self.stats['errors'] += 1
                return False
            
            # Process with Flask context and detailed logging
            logger.debug(f"[listener] Creating Flask context for message {message_id}")
            
            # Use existing Flask app instance instead of creating new one
            from flask import current_app
            try:
                # Try to use current app context if available
                if current_app:
                    success = await self.ingestion_service.handle_event({
                        'event_type': event_type,
                        'payload': data
                    })
                else:
                    raise RuntimeError("No Flask app context available")
            except RuntimeError:
                # Fall back to creating new app context
                logger.debug(f"[listener] No current app context, creating new one for {message_id}")
                from app import create_app
                app = create_app()
                
                with app.app_context():
                    success = await self.ingestion_service.handle_event({
                        'event_type': event_type,
                        'payload': data
                    })
            
            if success:
                logger.info(f"[listener] Successfully processed Discord event for message: {message_id}")
                self.stats['events_processed'] += 1
            else:
                logger.error(f"[listener] Failed to process Discord event for message: {message_id}")
                self.stats['errors'] += 1
            
            return success
                
        except Exception as e:
            logger.error(f"[listener] Error handling discord message event for {message_id}: {e}")
            import traceback
            logger.error(f"[listener] Traceback: {traceback.format_exc()}")
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
        
        # Start listener and wait for it to complete setup
        await _global_listener.start_listening()
        logger.info("Ingestion listener started successfully")
        
    except Exception as e:
        logger.error(f"Error starting ingestion listener: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


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