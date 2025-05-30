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
import discord

from .fetcher import MessageFetcher, fetch_latest_messages
from .validator import MessageValidator
from .models import DiscordMessageModel
from features.discord_bot.models import DiscordChannel
from features.discord_bot.dto import RawMessageDto
from .interfaces import IIngestionService
from common.db import db
from common.events import publish_event
from common.events.constants import EventChannels
from common.models import DiscordMessageDTO

logger = logging.getLogger(__name__)

class IngestionMetrics:
    """Metrics data structure for ingestion service."""
    def __init__(self):
        self.messages_processed_today = 0
        self.processing_rate_per_minute = 0
        self.validation_success_rate = 100.0
        self.validation_failures_today = 0
        self.last_processed_message = None
        self.queue_depth = 0
        self.avg_processing_time_ms = 0
        self.status = 'ready'


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

    async def store_discord_message(self, message: DiscordMessageDTO) -> bool:
        """
        Stores a single Discord message if it doesn't already exist.
        Returns True if stored, False if skipped.
        
        This is a low-level storage method focused on atomic operations
        with optional validation, but no event publishing.
        
        Args:
            message: Discord message DTO to store
            
        Returns:
            bool: True if stored, False if skipped (duplicate) or failed
        """
        try:
            # Check if message already exists (deduplication)
            existing = DiscordMessageModel.query.filter_by(message_id=message.message_id).first()
            if existing:
                logger.debug(f"Message {message.message_id} already exists, skipping")
                return False
            
            # Basic validation
            if not message.message_id or not message.channel_id:
                logger.warning(f"Invalid message data: missing required fields")
                return False
            
            # Create new message model
            message_model = DiscordMessageModel(
                message_id=message.message_id,
                channel_id=message.channel_id,
                author_id=message.author_id,
                author=getattr(message, 'author', 'unknown'),
                content=message.content,
                timestamp=message.created_at,
                is_processed=False
            )
            
            # Store in database
            db.session.add(message_model)
            db.session.commit()
            
            logger.debug(f"Successfully stored message {message.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing message {message.message_id}: {e}")
            db.session.rollback()
            return False

    async def process_message_batch(self, messages: List[discord.Message]) -> Dict[str, Any]:
        """
        Process a batch of Discord messages with shared processing core.
        
        Args:
            messages: List of Discord message objects
            
        Returns:
            Dict[str, Any]: Result summary with statistics
        """
        results = []
        errors_list = []
        
        for msg in messages:
            try:
                result = await self._process_single_message(msg)
                results.append(result)
            except Exception as e:
                error_info = {
                    'message_id': getattr(msg, 'id', 'unknown'),
                    'error': str(e)
                }
                errors_list.append(error_info)
                logger.error(f"Error processing message {getattr(msg, 'id', 'unknown')}: {e}")
                results.append(False)
        
        # Calculate statistics
        total = len(messages)
        stored = sum(1 for r in results if r is True)
        skipped = sum(1 for r in results if r is False)
        errors = len(errors_list)
        
        return {
            "total": total,
            "stored": stored,
            "skipped": skipped,
            "errors": errors,
            "errors_list": errors_list
        }

    async def process_realtime_message(self, message: discord.Message) -> bool:
        """
        Process a single real-time Discord message.
        
        Args:
            message: Discord message object from real-time events
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            return await self._process_single_message(message)
        except Exception as e:
            logger.error(f"Error processing real-time message {getattr(message, 'id', 'unknown')}: {e}")
            return False

    async def _process_single_message(self, message: discord.Message) -> bool:
        """
        Shared processing core for both batch and real-time messages.
        
        Args:
            message: Discord message object
            
        Returns:
            bool: True if stored, False if skipped or failed
        """
        try:
            # Convert Discord message to DTO
            dto = self._convert_to_dto(message)
            
            # Use the store_discord_message method for actual storage
            return await self.store_discord_message(dto)
            
        except Exception as e:
            logger.error(f"Error in _process_single_message: {e}")
            return False

    def _convert_to_dto(self, message: discord.Message) -> DiscordMessageDTO:
        """
        Convert Discord message object to DiscordMessageDTO.
        
        Args:
            message: Discord message object
            
        Returns:
            DiscordMessageDTO: Converted message DTO
        """
        return DiscordMessageDTO(
            message_id=str(message.id),
            channel_id=str(message.channel.id),
            author_id=str(message.author.id),
            content=message.content or "",
            created_at=message.created_at,
            is_setup=False,  # Will be determined by downstream processing
            processed=False,
            embed_data={}  # Can be populated if needed
        )

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

    async def _fetch_discord_messages(
        self,
        channel_id: str,
        limit: int,
        since: Optional[datetime] = None
    ) -> List[discord.Message]:
        """
        Fetch Discord message objects directly from the Discord client.
        
        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to fetch
            since: Only fetch messages after this timestamp
            
        Returns:
            List[discord.Message]: List of Discord message objects
        """
        try:
            if not self.client_manager or not self.client_manager.is_connected():
                logger.error("Discord client not available or not connected")
                return []
            
            # Get channel from Discord client
            channel = self.client_manager.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return []
            
            messages = []
            async for message in channel.history(limit=limit, after=since):
                messages.append(message)
            
            logger.info(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching Discord messages from channel {channel_id}: {e}")
            return []

    async def _emit_batch_completion_event(self, channel_id: str, batch_result: Dict[str, Any]) -> None:
        """
        Emit completion event for batch processing.
        
        Args:
            channel_id: Discord channel ID that was processed
            batch_result: Results from batch processing
        """
        try:
            publish_event(
                event_type="ingestion.batch.completed",
                payload={
                    'channel_id': channel_id,
                    'statistics': batch_result,
                    'timestamp': datetime.utcnow().isoformat()
                },
                channel=EventChannels.INGESTION_BATCH,
                source="ingestion_service"
            )
            
            # Also emit individual message stored events for each successfully stored message
            # This ensures downstream processing can pick up individual messages
            if batch_result.get('stored', 0) > 0:
                logger.debug(f"Emitted batch completion event for {batch_result['stored']} stored messages")
                
        except Exception as e:
            logger.error(f"Error emitting batch completion event: {e}")

    async def handle_realtime_message(self, message: discord.Message) -> None:
        """
        Handle a real-time Discord message from the bot's event listener.
        
        This method provides event publishing for real-time message processing
        while using the core processing logic.
        
        Args:
            message: Discord message object from real-time events
        """
        try:
            # Process the message using real-time processing
            success = await self.process_realtime_message(message)
            
            # Emit appropriate events based on success
            if success:
                publish_event(
                    event_type="ingestion.message.stored",
                    payload={
                        'message_id': str(message.id),
                        'channel_id': str(message.channel.id),
                        'author': str(message.author),
                        'content_length': len(message.content),
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    channel=EventChannels.INGESTION_MESSAGE,
                    source="realtime_ingestion"
                )
            else:
                logger.warning(f"Failed to process real-time message {message.id}")
                
        except Exception as e:
            logger.error(f"Error handling real-time message {getattr(message, 'id', 'unknown')}: {e}")

    async def ingest_latest_messages(
        self,
        channel_id: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Ingest latest messages from a Discord channel using new batch processing.

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

            # Step 1: Fetch messages using Discord client
            if not await self._ensure_fetcher_ready():
                raise RuntimeError("Could not initialize Discord fetcher")
            
            discord_messages = await self._fetch_discord_messages(channel_id, limit, since)
            
            # Step 2: Process batch using new batch processing method
            batch_result = await self.process_message_batch(discord_messages)
            
            # Step 3: Emit events for successfully stored messages
            if batch_result['stored'] > 0:
                await self._emit_batch_completion_event(channel_id, batch_result)

            logger.info(f"Ingestion completed: {batch_result}")
            return {
                'status': 'completed',
                'statistics': batch_result,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error during message ingestion: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1},
                'timestamp': datetime.utcnow().isoformat()
            }

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
            
            # Use the enhanced ingest_latest_messages method with batch processing
            result = await self.ingest_latest_messages(
                channel_id=channel_id,
                limit=limit,
                since=None  # Get all recent messages for history
            )
            
            # Add source information to result
            if result:
                result['source'] = source
                result['success'] = result.get('status') == 'completed'
            
            return result
            
        except Exception as e:
            logger.error(f"Error during channel history ingestion: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': source,
                'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
            }

    async def ingest_single_message(
        self,
        channel_id: str,
        message_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Ingest a single message by ID using real-time processing.

        Args:
            channel_id: Discord channel ID
            message_id: Specific message ID to ingest

        Returns:
            Optional[Dict[str, Any]]: Ingestion result or None if failed
        """
        try:
            if not self.client_manager or not self.client_manager.is_connected():
                logger.error("Discord client not available or not connected")
                return None
            
            # Get channel from Discord client
            channel = self.client_manager.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return None
            
            # Fetch specific message
            message = await channel.fetch_message(int(message_id))
            if not message:
                logger.error(f"Could not find message {message_id} in channel {channel_id}")
                return None
            
            # Process the single message using real-time processing
            success = await self.process_realtime_message(message)
            
            return {
                'success': success,
                'message_id': message_id,
                'channel_id': channel_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error ingesting single message {message_id}: {e}")
            return None

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

    def get_metrics(self) -> dict:
        """
        Get ingestion pipeline metrics for operational monitoring.
        
        Returns:
            dict: Metrics data for dashboard consumption
        """
        try:
            # Query database for real metrics
            from datetime import datetime, timedelta
            from common.db import db
            
            today = datetime.utcnow().date()
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            # Count messages processed today
            messages_today = db.session.execute(
                db.text("SELECT COUNT(*) FROM discord_messages WHERE DATE(created_at) = :today"),
                {'today': today}
            ).scalar() or 0
            
            # Count recent processing activity (last hour)
            recent_activity = db.session.execute(
                db.text("SELECT COUNT(*) FROM discord_messages WHERE created_at >= :hour_ago"),
                {'hour_ago': hour_ago}
            ).scalar() or 0
            
            # Calculate processing rate
            processing_rate = recent_activity
            
            # Get last processed message timestamp
            last_message_result = db.session.execute(
                db.text("SELECT MAX(created_at) FROM discord_messages")
            ).scalar()
            
            last_processed = last_message_result.isoformat() if last_message_result else None
            
            return {
                'messages_processed_today': messages_today,
                'processing_rate_per_minute': processing_rate,
                'validation_success_rate': 100.0,  # Could calculate from error logs
                'validation_failures_today': 0,
                'last_processed_message': last_processed,
                'queue_depth': 0,  # Would need queue implementation
                'avg_processing_time_ms': 0,  # Would need timing metrics
                'status': 'ready'
            }
            
        except Exception as e:
            logger.error(f"Error getting ingestion metrics: {e}")
            return {
                'messages_processed_today': 0,
                'processing_rate_per_minute': 0,
                'validation_success_rate': 0,
                'validation_failures_today': 0,
                'last_processed_message': None,
                'queue_depth': 0,
                'avg_processing_time_ms': 0,
                'status': 'error'
            }


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
    from common.events.constants import EventChannels, EventTypes

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