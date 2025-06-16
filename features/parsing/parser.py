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
from pytz import timezone, UTC

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
        
        # Trading day extraction pattern
        self.trading_day_pattern = re.compile(
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday)\s+([A-Z][a-z]+)\s+(\d{1,2})\b', 
            re.IGNORECASE
        )
    
    def _extract_trading_day(self, content: str) -> Optional[date]:
        """Extract trading day from message header like 'Thursday May 29'."""
        match = self.trading_day_pattern.search(content)
        if match:
            try:
                month_name = match.group(1)
                day = int(match.group(2))
                month = datetime.strptime(month_name, "%B").month
                year = datetime.now().year  # Could enhance this to roll over at year end
                extracted_date = date(year, month, day)
                logger.debug(f"Detected trading day: {extracted_date}")
                return extracted_date
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse trading day from '{match.group(0)}': {e}")
        return None
    
    def _normalize_timestamp_to_utc(self, raw_ts: str) -> datetime:
        """Normalize message timestamp to UTC timezone."""
        from common.utils import parse_discord_timestamp
        return parse_discord_timestamp(raw_ts)
    
    def _split_by_ticker_sections(self, content: str) -> Dict[str, str]:
        """Split message content by ticker sections to avoid over-parsing."""
        lines = content.splitlines()
        sections = {}
        current_ticker = None
        buffer = []

        for line in lines:
            stripped = line.strip()
            # Matches ticker line (e.g., NVDA, SPY, TSLA)
            if re.fullmatch(r'[A-Z]{1,5}', stripped):
                if current_ticker and buffer:
                    sections[current_ticker] = "\n".join(buffer).strip()
                current_ticker = stripped
                buffer = []
            elif current_ticker:
                buffer.append(stripped)
        
        if current_ticker and buffer:
            sections[current_ticker] = "\n".join(buffer).strip()
        
        logger.debug(f"Tickers found: {list(sections.keys())}")
        return sections
    
    def parse_message_to_setups(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Discord message into trading setups and levels.
        
        Args:
            raw_message: Dict containing message content, id, timestamp, etc.
            
        Returns:
            Dict containing success status, setups, levels, trading_day, and message_id
        """
        try:
            content = raw_message.get('content', '')
            message_id = raw_message.get('message_id', raw_message.get('id', ''))
            
            if not content.strip():
                logger.debug(f"Empty message content for {message_id}")
                return {
                    'success': False,
                    'setups': [],
                    'levels': [],
                    'trading_day': None,
                    'message_id': message_id
                }
            
            # Extract trading day from message header
            trading_day = self._extract_trading_day(content)
            
            # Fallback to normalized timestamp if trading day extraction fails
            if not trading_day and raw_message.get('timestamp'):
                from common.utils import get_trading_day
                utc_timestamp = self._normalize_timestamp_to_utc(raw_message['timestamp'])
                trading_day = get_trading_day(utc_timestamp)
            
            # Check if this is an A+ scalp setups message and route to specialized parser
            aplus_parser = get_aplus_parser()
            if aplus_parser.validate_message(content):
                logger.info(f"Routing message {message_id} to A+ specialized parser")
                result = aplus_parser.parse_message(content, message_id)
                
                if result.get('success') and result.get('setups'):
                    # Convert A+ DTOs to generic DTOs
                    setups = []
                    all_levels = []
                    
                    for trade_setup in result['setups']:
                        # Convert TradeSetup to ParsedSetupDTO
                        setup_dto = ParsedSetupDTO(
                            ticker=trade_setup.ticker,
                            setup_type=trade_setup.label,  # Use label as setup_type
                            bias_note=result.get('ticker_bias_notes', {}).get(trade_setup.ticker),
                            direction=trade_setup.direction,
                            confidence_score=0.8,  # A+ setups are high confidence
                            raw_content=trade_setup.raw_line,
                            parsed_metadata={
                                'setup_id': trade_setup.id,
                                'label': trade_setup.label,
                                'keywords': trade_setup.keywords,
                                'emoji_hint': trade_setup.emoji_hint,
                                'trigger_level': trade_setup.trigger_level,
                                'target_count': len(trade_setup.target_prices),
                                'parser_type': 'aplus_refactored'
                            }
                        )
                        setups.append(setup_dto)
                        
                        # Convert target prices to ParsedLevelDTO instances
                        for i, target_price in enumerate(trade_setup.target_prices):
                            level_dto = ParsedLevelDTO(
                                level_type='target',
                                direction=trade_setup.direction,
                                trigger_price=target_price,
                                strategy=trade_setup.label,
                                confidence=0.8,
                                description=f"Target {i+1} for {trade_setup.label or 'Unknown'}"
                            )
                            all_levels.append(level_dto)
                        
                        # Add trigger level as entry
                        if trade_setup.trigger_level:
                            entry_level = ParsedLevelDTO(
                                level_type='entry',
                                direction=trade_setup.direction,
                                trigger_price=trade_setup.trigger_level,
                                strategy=trade_setup.label,
                                confidence=0.8,
                                description=f"Entry trigger for {trade_setup.label or 'Unknown'}"
                            )
                            all_levels.append(entry_level)
                    
                    logger.info(f"A+ parser extracted {len(setups)} setups and {len(all_levels)} levels from message {message_id}")
                    return {
                        'success': True,
                        'setups': setups,
                        'levels': all_levels,
                        'trading_day': trading_day,
                        'message_id': message_id
                    }
                else:
                    logger.debug(f"A+ parser found no valid setups in message {message_id}")
                    return {
                        'success': False,
                        'setups': [],
                        'levels': [],
                        'trading_day': trading_day,
                        'message_id': message_id
                    }
            else:
                # Enforce A+ format - no fallback to generic parsing
                raise ValueError(f"Invalid format: message {message_id} does not match A+ pattern")
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return {
                'success': False,
                'setups': [],
                'levels': [],
                'trading_day': None,
                'message_id': raw_message.get('message_id', raw_message.get('id', ''))
            }
    
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
    
    def _parse_ticker_setup(self, ticker: str, content: str, raw_message: Dict) -> Tuple[Optional[Dict], List[ParsedLevelDTO]]:
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