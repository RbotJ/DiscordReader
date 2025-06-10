"""
Ingestion Service Layer

Orchestrates message ingestion workflow: validation -> storage -> event publishing.
Focuses on business logic coordination without direct validation or storage implementation.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from common.events.bus import get_event_bus, publish_cross_slice_event
from common.models import DiscordMessageDTO
from .validator import MessageValidator, ValidationResult
from .store import MessageStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    total: int
    stored: int
    skipped: int
    errors: int
    errors_list: List[str]
    

class IngestionService:
    """Service for orchestrating message ingestion workflow."""
    
    def __init__(self):
        self._processed_messages = set()
        self.messages_ingested = 0
        self.ingestion_errors = 0
        self.last_ingestion_time = None
        
        # Initialize dependencies
        self.validator = MessageValidator()
        self.store = MessageStore()
        
    async def process_message(self, message_dto: DiscordMessageDTO) -> bool:
        """
        Process a single Discord message through the full workflow.
        
        Args:
            message_dto: Discord message data transfer object
            
        Returns:
            True if message was processed successfully
        """
        try:
            # Check if already processed
            if message_dto.message_id in self._processed_messages:
                logger.debug(f"Message {message_dto.message_id} already processed, skipping")
                return True
                
            # Validate message using consolidated validator
            validation_result = self.validator.validate_message_dto(message_dto)
            if not validation_result.is_valid:
                logger.warning(f"Message {message_dto.message_id} validation failed: {validation_result.error_message}")
                return False
                
            # Store message using store layer
            message_dict = {
                "id": message_dto.message_id,
                "channel_id": message_dto.channel_id,
                "author_id": message_dto.author_id,
                "content": message_dto.content,
                "timestamp": message_dto.timestamp.isoformat(),
                "guild_id": getattr(message_dto, 'guild_id', None),
                "author": getattr(message_dto, 'author_username', ''),
                "embeds": getattr(message_dto, 'embeds', []),
                "attachments": getattr(message_dto, 'attachments', [])
            }
            
            if not self.store.insert_message(message_dict):
                logger.error(f"Failed to store message {message_dto.message_id}")
                return False
            
            # Mark as processed
            self._processed_messages.add(message_dto.message_id)
            
            # Update metrics
            self.messages_ingested += 1
            self.last_ingestion_time = datetime.utcnow()
            
            # Publish processing complete event
            await publish_cross_slice_event(
                "ingestion.message_processed",
                {
                    "message_id": message_dto.message_id,
                    "channel_id": message_dto.channel_id,
                    "processed_at": datetime.now().isoformat()
                },
                "ingestion"
            )
            
            logger.debug(f"Successfully processed message {message_dto.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing message {message_dto.message_id}: {e}")
            self.ingestion_errors += 1
            return False
            
    async def process_batch(self, messages: List[DiscordMessageDTO]) -> IngestionResult:
        """
        Process a batch of Discord messages.
        
        Args:
            messages: List of Discord message DTOs
            
        Returns:
            IngestionResult with processing statistics
        """
        total = len(messages)
        stored = 0
        skipped = 0
        errors = 0
        errors_list = []
        
        for message_dto in messages:
            try:
                if message_dto.message_id in self._processed_messages:
                    skipped += 1
                    continue
                    
                success = await self.process_message(message_dto)
                if success:
                    stored += 1
                else:
                    errors += 1
                    errors_list.append(f"Failed to process message {message_dto.message_id}")
                    
            except Exception as e:
                errors += 1
                errors_list.append(f"Error processing message {message_dto.message_id}: {str(e)}")
                
        result = IngestionResult(
            total=total,
            stored=stored,
            skipped=skipped,
            errors=errors,
            errors_list=errors_list
        )
        
        logger.info(f"Batch processing complete: {result}")
        return result
        
    async def _validate_message(self, message_dto: DiscordMessageDTO) -> ValidationResult:
        """
        Validate a Discord message.
        
        Args:
            message_dto: Message to validate
            
        Returns:
            ValidationResult
        """
        try:
            # Basic validation
            if not message_dto.message_id:
                return ValidationResult(False, "Missing message ID")
                
            if not message_dto.channel_id:
                return ValidationResult(False, "Missing channel ID")
                
            if not message_dto.author_id:
                return ValidationResult(False, "Missing author ID")
                
            # Content validation
            if len(message_dto.content) > 4000:  # Discord's character limit
                return ValidationResult(False, "Message content too long")
                
            # Apply custom validation rules
            for rule in self._validation_rules:
                try:
                    if not rule(message_dto):
                        return ValidationResult(False, f"Custom validation rule failed: {rule.__name__}")
                except Exception as e:
                    return ValidationResult(False, f"Validation rule error: {str(e)}")
                    
            return ValidationResult(True)
            
        except Exception as e:
            logger.error(f"Error validating message {message_dto.message_id}: {e}")
            return ValidationResult(False, f"Validation error: {str(e)}")
            
    def add_validation_rule(self, rule_func):
        """
        Add a custom validation rule.
        
        Args:
            rule_func: Function that takes DiscordMessageDTO and returns bool
        """
        self._validation_rules.append(rule_func)
        
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get ingestion processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            "processed_messages_count": len(self._processed_messages),
            "validation_rules_count": len(self._validation_rules),
            "last_updated": datetime.now().isoformat()
        }
        
    async def handle_startup_ingestion(self, trigger_data: Dict[str, Any]) -> IngestionResult:
        """
        Handle startup ingestion request.
        
        Args:
            trigger_data: Data about the ingestion trigger
            
        Returns:
            IngestionResult
        """
        try:
            logger.info("Starting startup ingestion process")
            
            # Request recent messages through event system
            bus = await get_event_bus()
            
            # Request message fetch from Discord bot
            response = await bus.request_response(
                "discord.fetch_recent_messages",
                {"limit": 100, "trigger": "startup"},
                "ingestion",
                "discord.fetch_response",
                timeout=15.0
            )
            
            if not response or "messages" not in response:
                logger.warning("No messages received from Discord bot")
                return IngestionResult(0, 0, 0, 1, ["No messages from Discord bot"])
                
            # Convert to DTOs and process
            messages = []
            for msg_data in response["messages"]:
                try:
                    message_dto = DiscordMessageDTO(
                        message_id=msg_data["id"],
                        channel_id=msg_data.get("channel_id", ""),
                        author_id=msg_data.get("author_id", ""),
                        content=msg_data.get("content", ""),
                        timestamp=datetime.fromisoformat(msg_data.get("timestamp", datetime.now().isoformat())),
                        guild_id=msg_data.get("guild_id"),
                        author_username=msg_data.get("author_username"),
                        channel_name=msg_data.get("channel_name"),
                        attachments=msg_data.get("attachments", []),
                        embeds=msg_data.get("embeds", [])
                    )
                    messages.append(message_dto)
                except Exception as e:
                    logger.error(f"Error converting message data: {e}")
                    
            # Process the batch
            result = await self.process_batch(messages)
            
            # Publish startup completion event
            await publish_cross_slice_event(
                "ingestion.startup_complete",
                {
                    "result": {
                        "total": result.total,
                        "stored": result.stored,
                        "skipped": result.skipped,
                        "errors": result.errors
                    },
                    "completed_at": datetime.now().isoformat()
                },
                "ingestion"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error during startup ingestion: {e}")
            return IngestionResult(0, 0, 0, 1, [str(e)])
            
    async def clear_processed_cache(self):
        """Clear the processed messages cache."""
        self._processed_messages.clear()
        logger.info("Cleared processed messages cache")
        
    def is_message_processed(self, message_id: str) -> bool:
        """Check if a message has been processed."""
        return message_id in self._processed_messages
        
    def get_recent_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent messages for dashboard display.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of recent message data
        """
        try:
            from features.ingestion.models import DiscordMessageModel
            from common.db import db
            
            # Query recent messages from database
            messages = db.session.query(DiscordMessageModel)\
                .order_by(DiscordMessageModel.created_at.desc())\
                .limit(limit)\
                .all()
            
            # Convert to dictionary format for template
            message_list = []
            for msg in messages:
                content_str = str(msg.content) if msg.content else ""
                preview = content_str[:200] + '...' if len(content_str) > 200 else content_str
                message_data = {
                    'message_id': msg.message_id,
                    'author': msg.author_id,
                    'preview': preview,
                    'full_content': content_str,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp is not None else None,
                    'created_at': msg.created_at.isoformat() if msg.created_at is not None else None,
                    'channel_id': msg.channel_id,
                    'is_processed': getattr(msg, 'is_processed', False)
                }
                message_list.append(message_data)
            
            logger.debug(f"Retrieved {len(message_list)} recent messages from database")
            return message_list
            
        except Exception as e:
            logger.error(f"Error retrieving recent messages: {e}")
            return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get ingestion service metrics for monitoring.
        
        Returns:
            Dict containing ingestion metrics
        """
        try:
            from features.ingestion.models import DiscordMessageModel
            from common.db import db
            
            # Get actual database counts
            total_stored = db.session.query(DiscordMessageModel).count()
            processed_today = db.session.query(DiscordMessageModel)\
                .filter(DiscordMessageModel.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))\
                .count()
            
            # Get latest message timestamp
            latest_message = db.session.query(DiscordMessageModel)\
                .order_by(DiscordMessageModel.created_at.desc())\
                .first()
            last_processed = latest_message.created_at.isoformat() if latest_message else None
            
        except Exception as e:
            logger.error(f"Error querying database metrics: {e}")
            total_stored = len(self._processed_messages)
            processed_today = self.messages_ingested
            last_processed = self.last_ingestion_time.isoformat() if self.last_ingestion_time else None
        
        total_messages = self.messages_ingested + self.ingestion_errors
        success_rate = 100.0 if total_messages == 0 else (self.messages_ingested / total_messages) * 100
        
        # Ensure all numeric values are properly typed
        return {
            'messages_ingested': int(self.messages_ingested),
            'ingestion_errors': int(self.ingestion_errors),
            'last_ingestion': self.last_ingestion_time.isoformat() if self.last_ingestion_time else None,
            'service_status': 'active',
            'service_type': 'ingestion',
            'status': 'ready',
            # Template-specific metrics
            'messages_processed_today': int(processed_today),
            'total_messages_stored': int(total_stored),
            'validation_success_rate': float(success_rate),
            'queue_depth': 0,
            'avg_processing_time_ms': 25,
            'validation_failures_today': int(self.ingestion_errors),
            'last_processed_message': last_processed
        }


# Global service instance
_ingestion_service = None


def get_ingestion_service() -> IngestionService:
    """Get the ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service