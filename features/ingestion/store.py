"""
Ingestion Store Module

Pure database storage layer for Discord message ingestion.
Handles raw database operations without business logic or event publishing.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from .models import DiscordMessageModel
from common.db import db

logger = logging.getLogger(__name__)


class MessageStore:
    """
    Pure storage layer for Discord messages.
    
    Handles database operations without business logic or event publishing.
    Focused on atomic operations with proper error handling.
    """
    
    def is_duplicate(self, message_id: str) -> bool:
        """
        Check if a message with the given ID already exists.
        
        Args:
            message_id: Discord message ID to check
            
        Returns:
            bool: True if message exists, False otherwise
        """
        try:
            existing = DiscordMessageModel.query.filter_by(message_id=message_id).first()
            return existing is not None
        except Exception as e:
            logger.error(f"Error checking for duplicate message {message_id}: {e}")
            return True  # Assume duplicate on error to prevent storage issues
    
    def insert_message(self, message: Dict[str, Any]) -> bool:
        """
        Insert a raw Discord message into the database.
        
        Args:
            message: Raw Discord message dictionary
            
        Returns:
            bool: True if inserted successfully, False otherwise
        """
        try:
            # Create model instance from dictionary
            message_model = DiscordMessageModel.from_dict(message)
            
            # Insert into database
            db.session.add(message_model)
            db.session.commit()
            
            logger.debug(f"Successfully inserted message {message.get('id')}")
            return True
            
        except IntegrityError as e:
            # Handle unique constraint violations (duplicate message_id)
            db.session.rollback()
            logger.warning(f"Duplicate message detected during insert: {message.get('id')}")
            return False
            
        except Exception as e:
            db.session.rollback()
            message_id = message.get('id', 'unknown')
            error_type = type(e).__name__
            logger.error(f"Error inserting message {message_id}: {error_type}: {e}")
            logger.error(f"Message content length: {len(str(message.get('content', '')))}")
            logger.error(f"Raw data type: {type(message.get('raw_data', 'None'))}")
            # Log first 200 chars of content for debugging
            content_preview = str(message.get('content', ''))[:200] + '...' if len(str(message.get('content', ''))) > 200 else str(message.get('content', ''))
            logger.error(f"Content preview: {content_preview}")
            return False
    
    def get_message_by_id(self, message_id: str) -> Optional[DiscordMessageModel]:
        """
        Retrieve a message by its Discord message ID.
        
        Args:
            message_id: Discord message ID
            
        Returns:
            Optional[DiscordMessageModel]: Message model or None if not found
        """
        try:
            return DiscordMessageModel.query.filter_by(message_id=message_id).first()
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            return None
    
    def get_unprocessed_messages(self, limit: Optional[int] = None) -> list[DiscordMessageModel]:
        """
        Get unprocessed messages from the database.
        
        Args:
            limit: Optional limit on number of messages to return
            
        Returns:
            List[DiscordMessageModel]: Unprocessed messages
        """
        try:
            query = DiscordMessageModel.query.filter_by(is_processed=False).order_by(
                DiscordMessageModel.timestamp.desc()
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving unprocessed messages: {e}")
            return []
    
    def mark_message_processed(self, message_id: str) -> bool:
        """
        Mark a message as processed.
        
        Args:
            message_id: Discord message ID to mark as processed
            
        Returns:
            bool: True if marked successfully, False otherwise
        """
        try:
            message = DiscordMessageModel.query.filter_by(message_id=message_id).first()
            if message:
                message.is_processed = True
                message.updated_at = datetime.utcnow()
                db.session.commit()
                return True
            else:
                logger.warning(f"Message {message_id} not found for processing update")
                return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking message {message_id} as processed: {e}")
            return False
    
    def get_message_count(self) -> int:
        """
        Get total count of stored messages.
        
        Returns:
            int: Total message count
        """
        try:
            return DiscordMessageModel.query.count()
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
    
    def get_processed_count(self) -> int:
        """
        Get count of processed messages.
        
        Returns:
            int: Processed message count
        """
        try:
            return DiscordMessageModel.query.filter_by(is_processed=True).count()
        except Exception as e:
            logger.error(f"Error getting processed message count: {e}")
            return 0
    
    def clear_all_messages(self) -> int:
        """
        Clear all stored messages from the database.
        
        Returns:
            int: Number of messages cleared
        """
        try:
            # Get count before deletion
            count = DiscordMessageModel.query.count()
            
            # Delete all messages
            DiscordMessageModel.query.delete()
            db.session.commit()
            
            logger.info(f"Cleared {count} messages from database")
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing messages: {e}")
            raise


# Global store instance
message_store = MessageStore()


# Convenience functions for backward compatibility
def is_duplicate(message_id: str) -> bool:
    """Check if message is a duplicate."""
    return message_store.is_duplicate(message_id)


def insert_message(message: Dict[str, Any]) -> bool:
    """Insert a message into the database."""
    return message_store.insert_message(message)


def get_message_by_id(message_id: str) -> Optional[DiscordMessageModel]:
    """Get message by ID."""
    return message_store.get_message_by_id(message_id)


def clear_all_messages() -> int:
    """Clear all stored messages from the database."""
    return message_store.clear_all_messages()