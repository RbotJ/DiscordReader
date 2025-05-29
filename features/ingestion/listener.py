"""
Ingestion Listener Module

Listens for MESSAGE_STORED events and triggers parsing workflow.
Enhanced with message processing patterns from legacy message consumer.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from common.db import get_latest_events, publish_event
from common.events.constants import EventChannels
from features.parsing.parser import MessageParser

logger = logging.getLogger(__name__)


class IngestionListener:
    """
    Enhanced ingestion listener with robust message processing workflow patterns.
    """
    
    def __init__(self):
        """Initialize the ingestion listener with enhanced capabilities."""
        self.parser = MessageParser()
        self.last_processed_event_id = None
        self.running = False
        self.processing_stats = {
            'messages_processed': 0,
            'setups_created': 0,
            'errors': 0,
            'last_activity': None
        }
    
    def start_listening(self, poll_interval: float = 5.0):
        """Start listening for ingestion events with configurable polling."""
        self.running = True
        logger.info(f"Ingestion listener started with {poll_interval}s poll interval")
        
        while self.running:
            try:
                self._process_pending_events()
                self._update_stats()
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping listener")
                break
            except Exception as e:
                logger.error(f"Error in listener main loop: {e}")
                self.processing_stats['errors'] += 1
                time.sleep(poll_interval)
    
    def _process_pending_events(self):
        """Process any pending MESSAGE_STORED events with error handling."""
        try:
            events = get_latest_events(
                EventChannels.DISCORD_MESSAGE,
                since_timestamp=self.last_processed_event_id,
                limit=10
            )
            
            if not events:
                return
            
            logger.debug(f"Processing {len(events)} pending events")
            
            for event in events:
                success = self._handle_message_stored_event(event)
                if success:
                    self.last_processed_event_id = event.get('id')
                    self.processing_stats['messages_processed'] += 1
                
        except Exception as e:
            logger.error(f"Error processing pending events: {e}")
            self.processing_stats['errors'] += 1
    
    def _handle_message_stored_event(self, event: Dict[str, Any]) -> bool:
        """Handle a MESSAGE_STORED event with enhanced error handling."""
        try:
            message_data = event.get('payload', {})
            message_content = message_data.get('content')
            message_id = message_data.get('message_id')
            
            if not message_content or not message_id:
                logger.warning(f"Invalid message event: {event}")
                return False
            
            # Skip if message is too short
            if len(message_content.strip()) < 10:
                logger.debug(f"Skipping short message {message_id}")
                return True
            
            # Parse the message
            setups = self.parser.parse_message(message_content, message_id)
            
            if setups:
                stored_count = 0
                for setup in setups:
                    if self._validate_setup(setup):
                        # Publish SETUP_PARSED event
                        publish_event(EventChannels.SETUP_CREATED, {
                            'ticker': setup.ticker,
                            'message_id': message_id,
                            'setup_type': getattr(setup, 'setup_type', 'unknown')
                        })
                        stored_count += 1
                
                logger.info(f"Processed {stored_count}/{len(setups)} setups from message {message_id}")
                self.processing_stats['setups_created'] += stored_count
                return stored_count > 0
            else:
                logger.debug(f"No setups found in message {message_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling message event: {e}")
            self.processing_stats['errors'] += 1
            return False
    
    def _validate_setup(self, setup: Any) -> bool:
        """Validate a setup object meets basic requirements."""
        try:
            if not hasattr(setup, 'ticker') or not setup.ticker:
                return False
            if not hasattr(setup, 'content') or not setup.content:
                return False
            if not setup.ticker.isalpha() or len(setup.ticker) > 5:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating setup: {e}")
            return False
    
    def _update_stats(self):
        """Update processing statistics."""
        self.processing_stats['last_activity'] = datetime.utcnow()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return self.processing_stats.copy()