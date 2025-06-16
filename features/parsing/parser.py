"""
Modern Message Parser

Single source of truth for parsing Discord messages into trade setups.
Uses the refactored A+ parser with TradeSetup dataclass and structured field mappings.
Legacy DTOs and regex-based parsing have been archived.
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pytz import timezone, UTC

from .aplus_parser import get_aplus_parser

logger = logging.getLogger(__name__)


class MessageParser:
    """
    Modern message parser that delegates to the refactored A+ parser.
    Legacy parsing methods have been archived.
    """
    
    def __init__(self):
        """Initialize parser with A+ integration."""
        self.aplus_parser = get_aplus_parser()
        logger.info("Modern message parser initialized with A+ integration")
    
    def parse_message(self, content: str, message_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Parse a Discord message for trading setups using the modern A+ parser.
        
        Args:
            content: Message content
            message_id: Optional message ID for tracking
            **kwargs: Additional context (timestamp, author_id, etc.)
            
        Returns:
            Dict containing parsing results with TradeSetup objects
        """
        try:
            # Check if trading_day already provided in kwargs (from A+ parser)
            provided_trading_day = kwargs.get('trading_day')
            
            # Use A+ parser for all messages
            if self.aplus_parser.validate_message(content):
                logger.info(f"Parsing message {message_id or 'unknown'} with A+ parser")
                result = self.aplus_parser.parse_message(content, message_id or 'unknown', **kwargs)
                
                # Don't override trading_day if A+ parser extracted it successfully
                if result.get('trading_date') and not provided_trading_day:
                    result['trading_day'] = result['trading_date']
                
                return result
            else:
                # Non-A+ messages are not parsed
                return {
                    'success': False,
                    'message': 'Message does not match A+ format',
                    'setups': [],
                    'levels': [],
                    'message_id': message_id
                }
            
        except Exception as e:
            logger.error(f"Error parsing message {message_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'setups': [],
                'levels': [],
                'message_id': message_id
            }
    
    def validate_message(self, content: str) -> bool:
        """
        Check if a message should be parsed for trading setups.
        
        Args:
            content: Message content to check
            
        Returns:
            True if message appears to be an A+ scalp setup message
        """
        return self.aplus_parser.validate_message(content)