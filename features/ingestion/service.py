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
from features.discord_bot.models import DiscordChannel
from features.discord_bot.dto import RawMessageDto
from .interfaces import IIngestionService
from common.db import db
from common.events import publish_event
from common.event_constants import EventChannels

logger = logging.getLogger(__name__)


class IngestionService(IIngestionService):
    """
    Orchestrates the Discord message ingestion workflow.

    This service manages the complete pipeline from fetching messages
    to storing them and emitting events for downstream processing.
    """

    def __init__(self, discord_client_manager=None):
        """
        Initialize ingestion service with required components.
        
        Args:
            discord_client_manager: Discord client manager instance (dependency injection)
        """
        self.client_manager = discord_client_manager
        self.fetcher = None  # Will be initialized with provided client
        self.validator = MessageValidator()
        self.last_triggered = None  # Track when ingestion was last triggered
        self.stats = {
            'total_fetched': 0,
            'total_validated': 0,
            'total_stored': 0,
            'total_errors': 0
        }

    async def ingest_raw_message(self, raw: RawMessageDto) -> None:
        """
        Ingest a single raw Discord message.
        
        Args:
            raw: Raw message DTO from Discord
        """
        try:
            logger.info(f"Ingesting raw message {raw.message_id}")
            
            # Check if message already exists
            existing = DiscordMessageModel.query.filter_by(message_id=raw.message_id).first()
            if existing:
                logger.debug(f"Message {raw.message_id} already exists, skipping")
                return
            
            # Create new message model
            message = DiscordMessageModel(
                message_id=raw.message_id,
                channel_id=raw.channel_id,
                author_id=raw.author_id,
                author=raw.author_name,
                content=raw.content,
                timestamp=raw.timestamp,
                is_processed=False
            )
            
            # Store in database
            db.session.add(message)
            db.session.commit()
            
            # Publish event for downstream processing
            publish_event(
                event_type="discord.message.stored",
                payload={
                    "message_id": raw.message_id,
                    "channel_id": raw.channel_id,
                    "content_preview": raw.content[:100] + "..." if len(raw.content) > 100 else raw.content
                },
                channel=EventChannels.DISCORD_MESSAGE,
                source="discord_ingestion"
            )
            
            logger.info(f"Successfully ingested message {raw.message_id}")
            
        except Exception as e:
            logger.error(f"Error ingesting raw message {raw.message_id}: {e}")
            db.session.rollback()
            raise

    async def _ensure_fetcher_ready(self) -> bool:
        """Ensure the message fetcher is ready with injected Discord client."""
        if self.fetcher is None:
            if self.client_manager and self.client_manager.is_connected():
                self.fetcher = MessageFetcher(self.client_manager)
                return True
            else:
                logger.error("Discord client manager not provided or not connected")
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
            # Record when ingestion was triggered for dashboard tracking
            self.last_triggered = datetime.utcnow()
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

    async def ingest_channel_history(
        self,
        channel_id: str,
        limit: int = 50,
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        Ingest channel message history for startup catchup or bulk processing.

        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to fetch
            source: Source of the ingestion request

        Returns:
            Dict[str, Any]: Ingestion results with statistics
        """
        try:
            logger.info(f"Starting channel history ingestion for {channel_id} (source: {source})")
            
            # Use the existing ingest_latest_messages method
            result = await self.ingest_latest_messages(
                channel_id=channel_id,
                limit=limit,
                since=None  # Get all recent messages for history
            )
            
            # Add source information to result
            if result:
                result['source'] = source
                result['success'] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error during channel history ingestion: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': source,
                'statistics': {'total_fetched': 0, 'total_stored': 0, 'total_errors': 1}
            }

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
        Ensures channel exists in discord_channels table before storing messages.

        Args:
            messages: List of valid messages to store

        Returns:
            List[DiscordMessageModel]: Stored message models
        """
        from common.db import db
        from features.discord_bot.models import DiscordChannel

        stored_messages = []

        try:
            # Begin transaction - process all messages in a single transaction
            for message_data in messages:
                # Ensure channel exists in discord_channels table
                channel_id = str(message_data['channel_id'])
                existing_channel = DiscordChannel.query.filter_by(channel_id=channel_id).first()
                
                if not existing_channel:
                    # Create channel record if it doesn't exist
                    new_channel = DiscordChannel(
                        channel_id=channel_id,
                        channel_name=f"Channel {channel_id}",  # Will be updated by channel manager
                        is_active=True
                    )
                    db.session.add(new_channel)
                    logger.info(f"Created channel record for {channel_id}")

                # Create model instance (no database operations)
                message_model = DiscordMessageModel.from_dict(message_data)
                # Add to session but don't commit yet
                db.session.add(message_model)
                stored_messages.append(message_model)

            # Commit all messages at once
            db.session.commit()
            logger.info(f"Successfully stored {len(stored_messages)} messages in batch")
            self.stats['total_stored'] += len(stored_messages)

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

    def get_last_triggered(self) -> Optional[datetime]:
        """
        Get timestamp of when ingestion was last triggered.
        Used by dashboard for operational telemetry.
        
        Returns:
            Optional[datetime]: Last triggered timestamp or None if never triggered
        """
        return self.last_triggered

    def _emit_message_stored_event(self, message) -> None:
        """
        Emit MESSAGE_STORED event for a successfully stored message.

        Args:
            message: Stored DiscordMessageModel instance
        """
        try:
            event_payload = {
                'message_id': message.message_id,
                'channel_id': message.channel_id,
                'content_length': len(message.content),
                'stored_at': datetime.utcnow().isoformat()
            }

            publish_event(
                event_type="MESSAGE_STORED",
                payload=event_payload,
                channel=EventChannels.DISCORD_MESSAGE
            )

        except Exception as e:
            logger.error(f"Error emitting MESSAGE_STORED event: {e}")

    def _notify_message_stored(self, message) -> None:
        """
        Send PostgreSQL NOTIFY for MESSAGE_STORED to trigger immediate processing.

        Args:
            message: Stored DiscordMessageModel instance
        """
        try:
            from common.db import db
            import json

            payload = json.dumps({
                'message_id': message.message_id,
                'channel_id': message.channel_id
            })

            # Send PostgreSQL NOTIFY
            db.session.execute(
                f"NOTIFY message_stored, '{payload}'"
            )
            db.session.commit()

        except Exception as e:
            logger.error(f"Error sending MESSAGE_STORED notification: {e}")


async def ingest_messages(limit: int = 50) -> int:
    """
    Main ingestion function following the specified interface.
    Fetches, validates, stores messages and emits MESSAGE_STORED events.

    Args:
        limit: Maximum number of messages to fetch

    Returns:
        int: Number of valid messages processed
    """
    from .fetcher import fetch_latest_messages
    from .validator import validate_message
    from common.db import db
    from common.events import publish_event
    from common.event_constants import EventChannels, EventTypes

    try:
        # Fetch messages from Discord
        messages = await fetch_latest_messages(limit)

        # Validate messages
        valid = [m for m in messages if validate_message(m)]

        # Store valid messages and emit events
        for msg_data in valid:
            # Create model instance
            msg_model = DiscordMessageModel.from_dict(msg_data)

            # Save to database
            db.session.add(msg_model)
            db.session.commit()

            # Emit MESSAGE_STORED event
            publish_event(
                event_type=EventTypes.INFO,
                payload={
                    'message_id': msg_model.message_id,
                    'channel_id': msg_model.channel_id,
                    'content': msg_model.content,
                    'author': msg_model.author,
                    'timestamp': msg_model.timestamp.isoformat()
                },
                channel=EventChannels.DISCORD_MESSAGE
            )

        logger.info(f"Ingested {len(valid)} valid messages out of {len(messages)} fetched")
        return len(valid)

    except Exception as e:
        logger.error(f"Error in message ingestion: {e}")
        db.session.rollback()
        raise


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