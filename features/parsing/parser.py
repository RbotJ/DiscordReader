"""
Consolidated Message Parser

Single source of truth for parsing Discord messages into trade setups.
Extracts ticker symbols, setup types, price levels, and trading bias from natural language text.
"""
import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, NamedTuple
from decimal import Decimal

from .aplus_parser import get_aplus_parser

logger = logging.getLogger(__name__)


class ParsedLevelDTO(NamedTuple):
    """Data transfer object for a parsed price level."""
    level_type: str  # entry, target, stop, bounce, rejection, breakout, breakdown
    direction: Optional[str]  # up, down, long, short
    trigger_price: float
    strategy: Optional[str]  # aggressive, conservative, normal
    confidence: Optional[float]  # 0.0 to 1.0
    description: Optional[str]


class ParsedSetupDTO(NamedTuple):
    """Data transfer object for a parsed trading setup."""
    ticker: str
    setup_type: Optional[str]  # breakout, breakdown, rejection, bounce
    bias_note: Optional[str]
    direction: Optional[str]  # bullish, bearish, neutral
    confidence_score: Optional[float]
    raw_content: str
    parsed_metadata: Optional[Dict[str, Any]]


class MessageParser:
    """
    Consolidated parser for Discord trading messages.
    Combines patterns from enhanced_parser.py and original parser.py.
    """
    
    def __init__(self):
        """Initialize parser with regex patterns and keywords."""
        # Ticker pattern - matches $AAPL, $SPY, etc.
        self.ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b', re.IGNORECASE)
        
        # Price patterns for different contexts
        self.price_patterns = {
            'entry': re.compile(r'(?:entry|enter)[\s:]*\$?(\d+(?:\.\d{1,4})?)', re.IGNORECASE),
            'target': re.compile(r'(?:target|tp)[\s:]*\$?(\d+(?:\.\d{1,4})?)', re.IGNORECASE),
            'stop': re.compile(r'(?:stop|sl|stop[\s-]?loss)[\s:]*\$?(\d+(?:\.\d{1,4})?)', re.IGNORECASE),
            'level': re.compile(r'(?:level|at|near)[\s:]*\$?(\d+(?:\.\d{1,4})?)', re.IGNORECASE),
            'resistance': re.compile(r'resistance[\s:]*\$?(\d+(?:\.\d{1,4})?)', re.IGNORECASE),
            'support': re.compile(r'support[\s:]*\$?(\d+(?:\.\d{1,4})?)', re.IGNORECASE)
        }
        
        # Setup type patterns
        self.setup_patterns = {
            'breakout': re.compile(r'\b(?:breakout|break[\s-]?out|breaking[\s-]?out)\b', re.IGNORECASE),
            'breakdown': re.compile(r'\b(?:breakdown|break[\s-]?down|breaking[\s-]?down)\b', re.IGNORECASE),
            'rejection': re.compile(r'\b(?:rejection|rejecting|reject)\b', re.IGNORECASE),
            'bounce': re.compile(r'\b(?:bounce|bouncing|bounced)\b', re.IGNORECASE)
        }
        
        # Direction and bias patterns
        self.direction_patterns = {
            'bullish': re.compile(r'\b(?:bullish|bull|long|buy|call|up)\b', re.IGNORECASE),
            'bearish': re.compile(r'\b(?:bearish|bear|short|sell|put|down)\b', re.IGNORECASE)
        }
        
        # Strategy patterns
        self.strategy_patterns = {
            'aggressive': re.compile(r'\b(?:aggressive|agro|high[\s-]?risk)\b', re.IGNORECASE),
            'conservative': re.compile(r'\b(?:conservative|safe|low[\s-]?risk)\b', re.IGNORECASE)
        }
        
        # Keywords that indicate a trading setup
        self.setup_keywords = [
            'setup', 'trade', 'signal', 'entry', 'target', 'stop', 'breakout', 'breakdown',
            'rejection', 'bounce', 'support', 'resistance', 'long', 'short', 'call', 'put'
        ]
    
    def parse_message_to_setups(self, raw_message: Dict[str, Any]) -> Tuple[List[ParsedSetupDTO], List[ParsedLevelDTO]]:
        """
        Parse a Discord message into trading setups and levels.
        
        Args:
            raw_message: Dict containing message content, id, timestamp, etc.
            
        Returns:
            Tuple of (setups, levels) extracted from the message
        """
        try:
            content = raw_message.get('content', '')
            message_id = raw_message.get('message_id', raw_message.get('id', ''))
            
            if not content.strip():
                logger.debug(f"Empty message content for {message_id}")
                return [], []
            
            # Extract tickers from message
            tickers = self._extract_tickers(content)
            if not tickers:
                logger.debug(f"No tickers found in message {message_id}")
                return [], []
            
            # Check if message contains trading setup keywords
            if not self._contains_setup_keywords(content):
                logger.debug(f"No setup keywords found in message {message_id}")
                return [], []
            
            setups = []
            all_levels = []
            
            # Process each ticker found
            for ticker in tickers:
                setup_dto, levels_dto = self._parse_ticker_setup(ticker, content, raw_message)
                if setup_dto:
                    setups.append(setup_dto)
                    all_levels.extend(levels_dto)
            
            logger.info(f"Parsed {len(setups)} setups and {len(all_levels)} levels from message {message_id}")
            return setups, all_levels
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return [], []
    
    def _extract_tickers(self, content: str) -> List[str]:
        """Extract ticker symbols from message content."""
        matches = self.ticker_pattern.findall(content)
        # Remove duplicates and convert to uppercase
        tickers = list(set(ticker.upper() for ticker in matches))
        return tickers
    
    def _contains_setup_keywords(self, content: str) -> bool:
        """Check if message contains trading setup keywords."""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.setup_keywords)
    
    def _parse_ticker_setup(self, ticker: str, content: str, raw_message: Dict) -> Tuple[Optional[ParsedSetupDTO], List[ParsedLevelDTO]]:
        """
        Parse setup information for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            content: Message content
            raw_message: Original message dict
            
        Returns:
            Tuple of (setup_dto, levels_list)
        """
        try:
            # Extract setup type
            setup_type = self._extract_setup_type(content)
            
            # Extract direction/bias
            direction = self._extract_direction(content)
            
            # Extract bias note (free-form text around the ticker)
            bias_note = self._extract_bias_note(ticker, content)
            
            # Calculate confidence score based on clarity of signals
            confidence_score = self._calculate_confidence(content, setup_type, direction)
            
            # Extract price levels
            levels = self._extract_price_levels(content, ticker)
            
            # Create metadata
            parsed_metadata = {
                'extracted_tickers': self._extract_tickers(content),
                'setup_keywords_found': [kw for kw in self.setup_keywords if kw in content.lower()],
                'price_levels_count': len(levels),
                'has_entry': any(level.level_type == 'entry' for level in levels),
                'has_target': any(level.level_type == 'target' for level in levels),
                'has_stop': any(level.level_type == 'stop' for level in levels)
            }
            
            # Only create setup if we have meaningful content
            if setup_type or direction or levels or any(kw in content.lower() for kw in ['entry', 'target', 'stop']):
                setup_dto = ParsedSetupDTO(
                    ticker=ticker,
                    setup_type=setup_type,
                    bias_note=bias_note,
                    direction=direction,
                    confidence_score=confidence_score,
                    raw_content=content,
                    parsed_metadata=parsed_metadata
                )
                return setup_dto, levels
            
            return None, []
            
        except Exception as e:
            logger.error(f"Error parsing ticker {ticker}: {e}")
            return None, []
    
    def _extract_setup_type(self, content: str) -> Optional[str]:
        """Extract setup type from content."""
        for setup_type, pattern in self.setup_patterns.items():
            if pattern.search(content):
                return setup_type
        return None
    
    def _extract_direction(self, content: str) -> Optional[str]:
        """Extract trading direction from content."""
        bullish_matches = len(self.direction_patterns['bullish'].findall(content))
        bearish_matches = len(self.direction_patterns['bearish'].findall(content))
        
        if bullish_matches > bearish_matches:
            return 'bullish'
        elif bearish_matches > bullish_matches:
            return 'bearish'
        return None
    
    def _extract_bias_note(self, ticker: str, content: str) -> Optional[str]:
        """Extract contextual bias information around the ticker."""
        # Find the ticker position and extract surrounding context
        ticker_pattern = re.compile(rf'\${ticker}\b', re.IGNORECASE)
        match = ticker_pattern.search(content)
        
        if match:
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 100)
            context = content[start:end].strip()
            
            # Clean up the context
            context = re.sub(r'\s+', ' ', context)
            return context if len(context) > len(ticker) + 5 else None
        
        return None
    
    def _calculate_confidence(self, content: str, setup_type: Optional[str], direction: Optional[str]) -> float:
        """Calculate confidence score based on parsing clarity."""
        score = 0.0
        
        # Base score for having content
        if content.strip():
            score += 0.1
        
        # Setup type identified
        if setup_type:
            score += 0.3
        
        # Direction identified
        if direction:
            score += 0.2
        
        # Has price levels
        price_matches = sum(len(pattern.findall(content)) for pattern in self.price_patterns.values())
        if price_matches > 0:
            score += min(0.3, price_matches * 0.1)
        
        # Has strategy indicators
        strategy_matches = sum(len(pattern.findall(content)) for pattern in self.strategy_patterns.values())
        if strategy_matches > 0:
            score += 0.1
        
        return min(1.0, score)
    
    def _extract_price_levels(self, content: str, ticker: str) -> List[ParsedLevelDTO]:
        """Extract price levels from content."""
        levels = []
        
        # Extract different types of price levels
        for level_type, pattern in self.price_patterns.items():
            matches = pattern.findall(content)
            for match in matches:
                try:
                    price = float(match)
                    
                    # Validate price is reasonable (basic sanity check)
                    if 0.01 <= price <= 10000:
                        # Determine strategy from surrounding context
                        strategy = self._extract_strategy_for_level(content, match)
                        
                        # Determine direction based on level type and overall direction
                        direction = self._determine_level_direction(level_type, content)
                        
                        level = ParsedLevelDTO(
                            level_type=level_type,
                            direction=direction,
                            trigger_price=price,
                            strategy=strategy,
                            confidence=0.8,  # Default confidence for extracted levels
                            description=f"{level_type.title()} level for {ticker}"
                        )
                        levels.append(level)
                        
                except (ValueError, TypeError):
                    continue
        
        # Remove duplicate levels (same type and price)
        unique_levels = []
        seen = set()
        for level in levels:
            key = (level.level_type, level.trigger_price)
            if key not in seen:
                seen.add(key)
                unique_levels.append(level)
        
        return unique_levels
    
    def _extract_strategy_for_level(self, content: str, price_match: str) -> Optional[str]:
        """Extract strategy context around a price level."""
        for strategy, pattern in self.strategy_patterns.items():
            if pattern.search(content):
                return strategy
        return 'normal'  # Default strategy
    
    def _determine_level_direction(self, level_type: str, content: str) -> Optional[str]:
        """Determine direction for a price level based on context."""
        overall_direction = self._extract_direction(content)
        
        # Map level types to likely directions
        if level_type in ['entry', 'target']:
            return overall_direction
        elif level_type == 'stop':
            # Stop loss is usually opposite direction
            if overall_direction == 'bullish':
                return 'down'
            elif overall_direction == 'bearish':
                return 'up'
        
        return overall_direction