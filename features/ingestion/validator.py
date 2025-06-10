"""
Message Validator Module

Consolidated validation logic for Discord messages.
Single source of truth for all message validation rules.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import re
from common.models import DiscordMessageDTO

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of message validation."""
    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message


class MessageValidator:
    """
    Consolidated validator for Discord messages.
    Single source of truth for all validation logic.
    """
    
    REQUIRED_FIELDS = ['id', 'content', 'author', 'timestamp', 'channel_id']
    MAX_CONTENT_LENGTH = 4000
    MIN_CONTENT_LENGTH = 1
    
    def __init__(self):
        """Initialize message validator with default rules."""
        self.validation_rules = self._load_validation_rules()
    
    def validate_message_dto(self, message_dto: DiscordMessageDTO) -> ValidationResult:
        """
        Validate a Discord message DTO.
        
        Args:
            message_dto: Message DTO to validate
            
        Returns:
            ValidationResult: Validation result with success status and error message
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
            if len(message_dto.content) > self.MAX_CONTENT_LENGTH:
                return ValidationResult(False, "Message content too long")
                
            if len(message_dto.content.strip()) < self.MIN_CONTENT_LENGTH:
                return ValidationResult(False, "Message content too short")
                
            # Apply custom validation rules
            for rule in self.validation_rules:
                try:
                    if not rule(message_dto):
                        return ValidationResult(False, f"Custom validation rule failed: {rule.__name__}")
                except Exception as e:
                    return ValidationResult(False, f"Validation rule error: {str(e)}")
                    
            return ValidationResult(True)
            
        except Exception as e:
            logger.error(f"Error validating message {message_dto.message_id}: {e}")
            return ValidationResult(False, f"Validation error: {str(e)}")
    
    def validate_message(self, message: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single Discord message dictionary.
        
        Args:
            message: Message dictionary to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Structural validation
        structural_errors = self._validate_structure(message)
        errors.extend(structural_errors)
        
        # Date validation
        date_errors = self._validate_dates(message)
        errors.extend(date_errors)
        
        # Content validation
        content_errors = self._validate_content(message)
        errors.extend(content_errors)
        
        return len(errors) == 0, errors
    
    def validate_message_batch(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of messages and return summary statistics.
        
        Args:
            messages: List of message dictionaries to validate
            
        Returns:
            Dict[str, Any]: Validation summary with valid/invalid counts and errors
        """
        pass
    
    def _validate_structure(self, message: Dict[str, Any]) -> List[str]:
        """
        Validate message structure and required fields.
        
        Args:
            message: Message dictionary
            
        Returns:
            List[str]: List of structural validation errors
        """
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in message:
                errors.append(f"Missing required field: {field}")
            elif not message[field] or str(message[field]).strip() == "":
                errors.append(f"Empty required field: {field}")
        
        return errors
    
    def _validate_dates(self, message: Dict[str, Any]) -> List[str]:
        """
        Validate message timestamp and date-related fields.
        
        Args:
            message: Message dictionary
            
        Returns:
            List[str]: List of date validation errors
        """
        errors = []
        
        if 'timestamp' in message:
            try:
                timestamp = self._parse_timestamp(message['timestamp'])
                if timestamp > datetime.now(timezone.utc):
                    errors.append("Message timestamp is in the future")
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid timestamp format: {e}")
        
        return errors
    
    def _validate_content(self, message: Dict[str, Any]) -> List[str]:
        """
        Validate message content length and format.
        
        Args:
            message: Message dictionary
            
        Returns:
            List[str]: List of content validation errors
        """
        errors = []
        
        if 'content' in message:
            content = str(message['content'])
            
            if len(content) > self.MAX_CONTENT_LENGTH:
                errors.append(f"Content too long: {len(content)} > {self.MAX_CONTENT_LENGTH}")
            
            if len(content.strip()) < self.MIN_CONTENT_LENGTH:
                errors.append(f"Content too short: {len(content.strip())} < {self.MIN_CONTENT_LENGTH}")
        
        return errors
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string into datetime object.
        
        Args:
            timestamp_str: Timestamp string to parse
            
        Returns:
            datetime: Parsed datetime object
        """
        # Handle various timestamp formats
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
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """
        Load validation rules configuration.
        
        Returns:
            Dict[str, Any]: Validation rules configuration
        """
        return {
            'max_content_length': self.MAX_CONTENT_LENGTH,
            'min_content_length': self.MIN_CONTENT_LENGTH,
            'required_fields': self.REQUIRED_FIELDS,
            'allow_future_timestamps': False
        }


def validate_message(message: Dict[str, Any]) -> bool:
    """
    Convenience function to validate a single message.
    Maintains backward compatibility with existing code.
    
    Args:
        message: Message dictionary to validate
        
    Returns:
        bool: True if message is valid, False otherwise
    """
    validator = MessageValidator()
    is_valid, _ = validator.validate_message(message)
    return is_valid


def validate_message_with_errors(message: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate message and return detailed error information.
    
    Args:
        message: Message dictionary to validate
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, error_list)
    """
    validator = MessageValidator()
    return validator.validate_message(message)


def validate_basic_message_fields(message: Dict[str, Any]) -> bool:
    """
    Basic validation matching the original Discord storage validation.
    Checks only core required fields: id, content, author, timestamp.
    
    Args:
        message: Message dictionary to validate
        
    Returns:
        bool: True if all required fields exist and are non-empty
    """
    required_fields = ['id', 'content', 'author', 'timestamp']
    
    # Check all required fields exist
    if not all(field in message for field in required_fields):
        return False
    
    # Check fields are not empty or None
    for field in required_fields:
        if not message[field] or str(message[field]).strip() == "":
            return False
    
    return True