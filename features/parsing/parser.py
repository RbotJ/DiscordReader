"""
Message Parser Module

Handles parsing of Discord messages using regex and NLP techniques.
Converts raw message text into structured SetupModel instances.
This module focuses on extracting trading setups from natural language text.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime, date

from common.parser_utils import (
    normalize_text,
    extract_ticker_sections,
    process_ticker_sections,
    extract_signal_from_section,
    extract_bias_from_section
)
from .models import SetupModel

logger = logging.getLogger(__name__)


class MessageParser:
    """
    Parses Discord messages to extract trading setup information.
    
    This class uses a combination of regex patterns and natural language
    processing to identify and extract trading setups from message content.
    """
    
    def __init__(self):
        """Initialize message parser with parsing rules and patterns."""
        self.ticker_pattern = re.compile(r'\$([A-Z]{1,5})', re.IGNORECASE)
        self.price_pattern = re.compile(r'\$?(\d+(?:\.\d{1,2})?)', re.IGNORECASE)
        self.setup_keywords = [
            'breakout', 'breakdown', 'rejection', 'bounce', 'support', 'resistance',
            'long', 'short', 'call', 'put', 'bullish', 'bearish'
        ]
    
    def parse_message(self, message_content: str, message_id: str) -> List[SetupModel]:
        """
        Parse a Discord message to extract trading setups.
        
        Args:
            message_content: Raw message content to parse
            message_id: Discord message ID for reference
            
        Returns:
            List[SetupModel]: List of extracted trading setups
        """
        try:
            # Normalize the text for consistent parsing
            normalized_text = normalize_text(message_content)
            
            # Extract ticker sections
            ticker_sections = extract_ticker_sections(normalized_text)
            
            if not ticker_sections:
                logger.debug(f"No ticker sections found in message {message_id}")
                return []
            
            # Process each ticker section to extract setups
            setups = []
            for section in ticker_sections:
                setup = self._parse_ticker_section(section, message_id)
                if setup:
                    setups.append(setup)
            
            logger.info(f"Parsed {len(setups)} setups from message {message_id}")
            return setups
            
        except Exception as e:
            logger.error(f"Error parsing message {message_id}: {e}")
            return []
    
    def parse_batch_messages(self, messages: List[Dict[str, Any]]) -> List[SetupModel]:
        """
        Parse multiple messages in batch for efficiency.
        
        Args:
            messages: List of message dictionaries to parse
            
        Returns:
            List[SetupModel]: All extracted setups from all messages
        """
        all_setups = []
        
        for message in messages:
            content = message.get('content', '')
            message_id = message.get('message_id', message.get('id', ''))
            
            setups = self.parse_message(content, message_id)
            all_setups.extend(setups)
        
        return all_setups
    
    def _parse_ticker_section(self, section, message_id: str) -> Optional[SetupModel]:
        """
        Parse an individual ticker section to extract setup information.
        
        Args:
            section: TickerSection object containing ticker and content
            message_id: Discord message ID for reference
            
        Returns:
            Optional[SetupModel]: Parsed setup or None if no valid setup found
        """
        try:
            # Extract basic setup information
            setup_type = self._classify_setup_type(section.content)
            direction = self._extract_direction(section.content)
            price_target = self._extract_primary_price(section.content)
            confidence = self._calculate_confidence(section.content, setup_type)
            
            # Create setup model
            setup = SetupModel(
                ticker=section.ticker,
                setup_type=setup_type,
                direction=direction,
                price_target=price_target,
                confidence=confidence,
                context=section.content,
                source_message_id=message_id,
                date=date.today(),
                created_at=datetime.utcnow()
            )
            
            return setup
            
        except Exception as e:
            logger.error(f"Error parsing ticker section for {section.ticker}: {e}")
            return None
    
    def _classify_setup_type(self, content: str) -> str:
        """
        Classify the type of trading setup based on content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            str: Classified setup type
        """
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['breakout', 'break out', 'breaking']):
            return 'breakout'
        elif any(word in content_lower for word in ['breakdown', 'break down', 'falling']):
            return 'breakdown'
        elif any(word in content_lower for word in ['rejection', 'reject', 'bounce off']):
            return 'rejection'
        elif any(word in content_lower for word in ['bounce', 'bouncing', 'support']):
            return 'bounce'
        elif any(word in content_lower for word in ['call', 'calls', 'long']):
            return 'call_setup'
        elif any(word in content_lower for word in ['put', 'puts', 'short']):
            return 'put_setup'
        else:
            return 'unknown'
    
    def _extract_direction(self, content: str) -> str:
        """
        Extract trading direction from content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            str: Trading direction (bullish/bearish)
        """
        content_lower = content.lower()
        
        bullish_indicators = ['bullish', 'long', 'call', 'calls', 'up', 'higher', 'above']
        bearish_indicators = ['bearish', 'short', 'put', 'puts', 'down', 'lower', 'below']
        
        bullish_count = sum(1 for indicator in bullish_indicators if indicator in content_lower)
        bearish_count = sum(1 for indicator in bearish_indicators if indicator in content_lower)
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _extract_primary_price(self, content: str) -> Optional[float]:
        """
        Extract the primary price target from content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Optional[float]: Primary price target or None
        """
        prices = self.price_pattern.findall(content)
        if prices:
            try:
                return float(prices[0])
            except ValueError:
                pass
        return None
    
    def _calculate_confidence(self, content: str, setup_type: str) -> float:
        """
        Calculate confidence score for the parsed setup.
        
        Args:
            content: Text content to analyze
            setup_type: Type of setup identified
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Adjust based on setup type clarity
        if setup_type != 'unknown':
            confidence += 0.2
        
        # Adjust based on presence of price targets
        if self._extract_primary_price(content):
            confidence += 0.1
        
        # Adjust based on content length and detail
        if len(content) > 50:
            confidence += 0.1
        
        # Adjust based on keyword density
        keyword_count = sum(1 for keyword in self.setup_keywords 
                          if keyword.lower() in content.lower())
        confidence += min(keyword_count * 0.05, 0.2)
        
        return min(confidence, 1.0)


def parse_message_content(content: str, message_id: str = '') -> List[SetupModel]:
    """
    Convenience function to parse message content.
    
    Args:
        content: Message content to parse
        message_id: Optional message ID for reference
        
    Returns:
        List[SetupModel]: Extracted trading setups
    """
    parser = MessageParser()
    return parser.parse_message(content, message_id)