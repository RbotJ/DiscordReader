"""
Message Processor Module

Pure message processing logic separated from service orchestration.
Handles the core business logic of message transformation and preparation.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
from common.models import DiscordMessageDTO
from common.utils import parse_discord_timestamp, utc_now

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Pure message processing logic.
    Handles message transformation and preparation without side effects.
    """
    
    def __init__(self):
        """Initialize message processor."""
        self.processing_stats = {
            'messages_processed': 0,
            'transformation_errors': 0,
            'last_processed': None
        }
    
    def transform_discord_message(self, raw_message: Dict[str, Any]) -> DiscordMessageDTO:
        """
        Transform raw Discord message data to DTO.
        
        Args:
            raw_message: Raw message dictionary from Discord API
            
        Returns:
            DiscordMessageDTO: Transformed message object
        """
        try:
            # Parse timestamp
            timestamp_str = raw_message.get('timestamp')
            if isinstance(timestamp_str, str):
                timestamp = self._parse_timestamp(timestamp_str)
            else:
                timestamp = timestamp_str or datetime.utcnow()
            
            # Create DTO
            message_dto = DiscordMessageDTO(
                message_id=str(raw_message['id']),
                channel_id=str(raw_message['channel_id']),
                author_id=str(raw_message.get('author_id', raw_message.get('author', ''))),
                content=str(raw_message['content']),
                timestamp=timestamp,
                guild_id=raw_message.get('guild_id'),
                author_username=raw_message.get('author', ''),
                channel_name=raw_message.get('channel_name', ''),
                attachments=raw_message.get('attachments', []),
                embeds=raw_message.get('embeds', [])
            )
            
            self.processing_stats['messages_processed'] += 1
            self.processing_stats['last_processed'] = datetime.utcnow()
            
            return message_dto
            
        except Exception as e:
            logger.error(f"Error transforming message {raw_message.get('id')}: {e}")
            self.processing_stats['transformation_errors'] += 1
            raise
    
    def transform_batch(self, raw_messages: List[Dict[str, Any]]) -> List[DiscordMessageDTO]:
        """
        Transform a batch of raw Discord messages to DTOs.
        
        Args:
            raw_messages: List of raw message dictionaries
            
        Returns:
            List[DiscordMessageDTO]: List of transformed message objects
        """
        transformed_messages = []
        
        for raw_message in raw_messages:
            try:
                message_dto = self.transform_discord_message(raw_message)
                transformed_messages.append(message_dto)
            except Exception as e:
                logger.error(f"Failed to transform message {raw_message.get('id')}: {e}")
                # Continue processing other messages
                continue
        
        return transformed_messages
    
    def prepare_message_for_storage(self, message_dto: DiscordMessageDTO) -> Dict[str, Any]:
        """
        Prepare message DTO for database storage.
        
        Args:
            message_dto: Message DTO to prepare
            
        Returns:
            Dict[str, Any]: Message dictionary ready for storage
        """
        from common.utils import ensure_utc
        
        # Import make_json_serializable locally to avoid circular imports
        def make_json_serializable(obj):
            """Convert objects to JSON-serializable format."""
            from datetime import datetime
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {key: make_json_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            else:
                return obj
        
        # Create raw_data from the DTO fields
        raw_data = {
            "id": message_dto.message_id,
            "channel_id": message_dto.channel_id,
            "author_id": message_dto.author_id,
            "content": message_dto.content,
            "timestamp": message_dto.timestamp.isoformat() if message_dto.timestamp else None,
            "guild_id": getattr(message_dto, 'guild_id', None),
            "author_username": getattr(message_dto, 'author_username', ''),
            "embeds": getattr(message_dto, 'embeds', []),
            "attachments": getattr(message_dto, 'attachments', [])
        }
        
        return {
            "id": message_dto.message_id,
            "channel_id": message_dto.channel_id,
            "author_id": message_dto.author_id,
            "content": message_dto.content,
            "timestamp": ensure_utc(message_dto.timestamp),  # Store as timezone-aware datetime
            "guild_id": getattr(message_dto, 'guild_id', None),
            "author": getattr(message_dto, 'author_username', ''),
            "embeds": getattr(message_dto, 'embeds', []),
            "attachments": getattr(message_dto, 'attachments', []),
            "raw_data": make_json_serializable(raw_data)  # Include raw_data with proper serialization
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string into datetime object.
        
        Args:
            timestamp_str: Timestamp string to parse
            
        Returns:
            datetime: Parsed datetime object
        """
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse timestamp: {timestamp_str}")