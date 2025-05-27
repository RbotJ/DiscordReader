
"""
Discord Service - Central Orchestrator

Coordinates the Discord message workflow: fetch → validate → store → publish
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .fetcher import fetch_latest_messages
from .storage import store_message, validate_message
from .events import publish_message_stored_event

logger = logging.getLogger(__name__)

class DiscordService:
    """Central service for Discord message operations"""
    
    def __init__(self):
        self.logger = logger
    
    async def process_latest_messages(self, limit: int = 50) -> Dict[str, Any]:
        """
        Main workflow: fetch → validate → store → publish
        
        Returns:
            Summary of processing results
        """
        results = {
            'fetched': 0,
            'stored': 0,
            'published': 0,
            'errors': []
        }
        
        try:
            # Step 1: Fetch messages
            messages = await fetch_latest_messages(limit)
            results['fetched'] = len(messages)
            
            if not messages:
                self.logger.warning("No messages fetched")
                return results
            
            # Step 2: Process each message
            for message in messages:
                try:
                    # Validate
                    if not validate_message(message):
                        self.logger.warning(f"Invalid message format: {message.get('id')}")
                        continue
                    
                    # Store
                    stored_id = store_message(message)
                    if stored_id:
                        results['stored'] += 1
                        
                        # Publish event
                        if publish_message_stored_event(message, stored_id):
                            results['published'] += 1
                        else:
                            self.logger.warning(f"Failed to publish event for message {stored_id}")
                    
                except Exception as e:
                    error_msg = f"Error processing message {message.get('id')}: {e}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            return results
            
        except Exception as e:
            error_msg = f"Service error: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    async def fetch_and_store_single_message(self) -> Optional[int]:
        """Convenience method for fetching and storing a single message"""
        results = await self.process_latest_messages(limit=1)
        return results['stored'] if results['stored'] > 0 else None

# Global service instance
discord_service = DiscordService()
