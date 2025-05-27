"""
Ingestion Service Module

Orchestrates the complete Discord message ingestion workflow:
fetch → validate → store → emit MESSAGE_STORED event.

This service coordinates between the fetcher, validator, and storage components
to provide a unified interface for message ingestion.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .fetcher import MessageFetcher, fetch_latest_messages
from .validator import MessageValidator
from .models import DiscordMessageModel
from .discord import get_discord_client, ensure_discord_connection
from common.db import publish_event
from common.event_constants import EventChannels

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Orchestrates the Discord message ingestion workflow.
    
    This service manages the complete pipeline from fetching messages
    to storing them and emitting events for downstream processing.
    """
    
    def __init__(self):
        """Initialize ingestion service with required components."""
        self.fetcher = None  # Will be initialized with Discord client
        self.validator = MessageValidator()
        self.stats = {
            'total_fetched': 0,
            'total_validated': 0,
            'total_stored': 0,
            'total_errors': 0
        }
    
    async def _ensure_fetcher_ready(self) -> bool:
        """Ensure the message fetcher is ready with Discord connection."""
        if self.fetcher is None:
            client_manager = await ensure_discord_connection()
            if client_manager:
                self.fetcher = MessageFetcher(client_manager)
                return True
            return False
        return True
    
    async def ingest_latest_messages(
        self,
        channel_id: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Ingest latest messages from a Discord channel.
        
        Args:
            channel_id: Discord channel ID to fetch from
            limit: Maximum number of messages to fetch
            since: Only fetch messages after this timestamp
            
        Returns:
            Dict[str, Any]: Ingestion results with statistics
        """
        try:
            logger.info(f"Starting message ingestion for channel {channel_id}")
            
            # Step 1: Fetch messages
            messages = await self._fetch_messages(channel_id, limit, since)
            self.stats['total_fetched'] = len(messages)
            
            # Step 2: Validate messages
            valid_messages = self._validate_messages(messages)
            self.stats['total_validated'] = len(valid_messages)
            
            # Step 3: Store messages
            stored_messages = await self._store_messages(valid_messages)
            self.stats['total_stored'] = len(stored_messages)
            
            # Step 4: Emit events for stored messages
            await self._emit_message_events(stored_messages)
            
            logger.info(f"Ingestion completed: {self.stats}")
            return self._create_ingestion_result()
            
        except Exception as e:
            logger.error(f"Error during message ingestion: {e}")
            self.stats['total_errors'] += 1
            raise
    
    async def ingest_single_message(
        self,
        channel_id: str,
        message_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Ingest a single message by ID.
        
        Args:
            channel_id: Discord channel ID
            message_id: Specific message ID to ingest
            
        Returns:
            Optional[Dict[str, Any]]: Ingestion result or None if failed
        """
        pass
    
    async def _fetch_messages(
        self,
        channel_id: str,
        limit: int,
        since: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages using the message fetcher.
        
        Args:
            channel_id: Discord channel ID
            limit: Message limit
            since: Since timestamp
            
        Returns:
            List[Dict[str, Any]]: Fetched messages
        """
        # Ensure fetcher is ready
        if not await self._ensure_fetcher_ready():
            raise RuntimeError("Could not initialize Discord fetcher")
        
        return await self.fetcher.fetch_latest_messages(channel_id, limit, since)
    
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate messages using the message validator.
        
        Args:
            messages: List of messages to validate
            
        Returns:
            List[Dict[str, Any]]: Valid messages only
        """
        valid_messages = []
        
        for message in messages:
            is_valid, errors = self.validator.validate_message(message)
            if is_valid:
                valid_messages.append(message)
            else:
                logger.warning(f"Invalid message {message.get('id', 'unknown')}: {errors}")
                self.stats['total_errors'] += 1
        
        return valid_messages
    
    async def _store_messages(self, messages: List[Dict[str, Any]]) -> List[DiscordMessageModel]:
        """
        Store validated messages in the database with proper transaction management.
        
        Args:
            messages: List of valid messages to store
            
        Returns:
            List[DiscordMessageModel]: Stored message models
        """
        from common.db import db
        
        stored_messages = []
        
        try:
            # Begin transaction - process all messages in a single transaction
            for message_data in messages:
                # Create model instance (no database operations)
                message_model = DiscordMessageModel.from_dict(message_data)
                # Add to session but don't commit yet
                db.session.add(message_model)
                stored_messages.append(message_model)
            
            # Commit all messages at once
            db.session.commit()
            logger.info(f"Successfully stored {len(stored_messages)} messages in batch")
            
        except Exception as e:
            # Rollback the entire batch if any message fails
            db.session.rollback()
            logger.error(f"Error storing message batch: {e}")
            self.stats['total_errors'] += len(messages)
            stored_messages = []  # Clear the list since nothing was actually stored
            raise
        
        return stored_messages
    
    async def _emit_message_events(self, stored_messages: List[DiscordMessageModel]) -> None:
        """
        Emit MESSAGE_STORED events for each stored message.
        
        Args:
            stored_messages: List of stored message models
        """
        for message in stored_messages:
            try:
                event_payload = {
                    'message_id': message.message_id,
                    'channel_id': message.channel_id,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'author': message.author
                }
                
                publish_event(
                    event_type="MESSAGE_STORED",
                    payload=event_payload,
                    channel=EventChannels.DISCORD_MESSAGE
                )
                
            except Exception as e:
                logger.error(f"Error emitting event for message {message.message_id}: {e}")
    
    def _create_ingestion_result(self) -> Dict[str, Any]:
        """
        Create ingestion result summary.
        
        Returns:
            Dict[str, Any]: Ingestion statistics and status
        """
        return {
            'status': 'completed',
            'statistics': self.stats.copy(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def reset_stats(self) -> None:
        """Reset ingestion statistics."""
        self.stats = {
            'total_fetched': 0,
            'total_validated': 0,
            'total_stored': 0,
            'total_errors': 0
        }


async def ingest_channel_messages(
    channel_id: str,
    limit: int = 100,
    since: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Convenience function to ingest messages from a channel.
    
    Args:
        channel_id: Discord channel ID to ingest from
        limit: Maximum number of messages to fetch
        since: Only fetch messages after this timestamp
        
    Returns:
        Dict[str, Any]: Ingestion results
    """
    service = IngestionService()
    return await service.ingest_latest_messages(channel_id, limit, since)