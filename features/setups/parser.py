"""
Setup Parser Module

This module provides parsing functions for trading setup messages,
supporting multiple ticker symbols and various message formats.
"""
import logging
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union, Set, Tuple

from common.schemas import (
    TradeSetupDTO,
    TickerSetupDTO,
    SignalDTO,
    BiasDTO,
    BiasFlipDTO,
    SignalCategoryDTO,
    AggressivenessDTO,
    ComparisonTypeDTO,
    BiasDirectionDTO
)

# Global parser instance for the functional API
_parser = None

def parse_setup_message(
    message_text: str,
    setup_date: Optional[date] = None,
    source: str = "unknown"
) -> TradeSetupDTO:
    """
    Parse a setup message into structured data.
    
    This is a functional wrapper around the SetupParser class for backwards compatibility.
    
    Args:
        message_text: Raw setup message text
        setup_date: Date of the setup message (defaults to today)
        source: Source of the setup message
        
    Returns:
        TradeSetupDTO: Parsed setup data
    """
    global _parser
    
    # Initialize parser if needed
    if _parser is None:
        _parser = SetupParser()
    
    # Use today's date if no date provided
    if setup_date is None:
        setup_date = datetime.now().date()
    
    # Process the message
    ticker_sections = _parser.extract_ticker_sections(message_text)
    ticker_setups = []
    
    for ticker, section_text in ticker_sections.items():
        # Extract signals and bias for this ticker
        signals = _parser.extract_signals(ticker, section_text)
        bias = _parser.extract_bias(ticker, section_text)
        
        # Create ticker setup
        ticker_setup = TickerSetupDTO(
            symbol=ticker,
            text=section_text,
            signals=signals,
            bias=bias
        )
        
        ticker_setups.append(ticker_setup)
    
    # Create and return setup message
    # Ensure setup_date is not None
    actual_date = setup_date if setup_date is not None else datetime.now().date()
    
    return TradeSetupDTO(
        date=actual_date,
        raw_text=message_text,
        source=source,
        ticker_setups=ticker_setups
    )
import logging
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union, Set, Tuple

from common.schemas import (
    TradeSetupDTO,
    TickerSetupDTO,
    SignalDTO,
    BiasDTO,
    BiasFlipDTO,
    SignalCategoryDTO,
    AggressivenessDTO,
    ComparisonTypeDTO,
    BiasDirectionDTO
)

# Configure logger
logger = logging.getLogger(__name__)

class SetupParser:
    """Parser for trading setup messages with multi-ticker support."""
    
    def __init__(self):
        """Initialize the setup parser."""
        # Define standard emoji/text mappings for signal categories
        self.emoji_map = {
            # Breakout indicators
            "🔼": "[BREAKOUT]",
            "⬆️": "[BREAKOUT]",
            "🚀": "[BREAKOUT]",
            "🔝": "[BREAKOUT]",
            
            # Breakdown indicators
            "🔽": "[BREAKDOWN]",
            "⬇️": "[BREAKDOWN]",
            "📉": "[BREAKDOWN]",
            "🔻": "[BREAKDOWN]",
            
            # Rejection indicators
            "❌": "[REJECTION]",
            "🚫": "[REJECTION]",
            "🛑": "[REJECTION]",
            "⛔": "[REJECTION]",
            
            # Bounce indicators
            "🔄": "[BOUNCE]",
            "↩️": "[BOUNCE]",
            "↪️": "[BOUNCE]",
            "🔙": "[BOUNCE]",
            
            # Warning/Alert indicators
            "⚠️": "[WARNING]",
            "🔔": "[WARNING]",
            "📢": "[WARNING]",
            "🚨": "[WARNING]",
        }
        
        # Pattern for extracting ticker symbols
        self.ticker_pattern = r'\b[A-Z]{1,5}\b'
        
        # Patterns for detecting different message formats
        self.section_patterns = {
            "numbered_with_parenthesis": r'(?ms)^\s*\d+\)\s+([A-Z]{1,5}):\s*(.*?)(?=^\s*\d+\)\s+[A-Z]{1,5}:|\Z)',
            "numbered_with_period": r'(?ms)^\s*\d+\.\s+([A-Z]{1,5}):\s*(.*?)(?=^\s*\d+\.\s+[A-Z]{1,5}:|\Z)',
            "ticker_colon": r'(?ms)^([A-Z]{1,5}):\s*(.*?)(?=^[A-Z]{1,5}:|\Z)',
            "ticker_standalone": r'(?ms)^([A-Z]{1,5})$\s*(.*?)(?=^[A-Z]{1,5}$|\Z)'
        }
        
        # Signal extraction patterns
        self.signal_patterns = {
            "breakout": [
                r'\b(?:breakout|break out|breaking out|breaking)\s+(?:above|over|past)\s+(\d+(?:\.\d+)?)',
                r'\[BREAKOUT\].*?(?:above|over|past)\s+(\d+(?:\.\d+)?)',
                r'(?:buying|long|calls)\s+(?:above|over|past)\s+(\d+(?:\.\d+)?)'
            ],
            "breakdown": [
                r'\b(?:breakdown|break down|breaking down)\s+(?:below|under|beneath)\s+(\d+(?:\.\d+)?)',
                r'\[BREAKDOWN\].*?(?:below|under|beneath)\s+(\d+(?:\.\d+)?)',
                r'(?:selling|short|puts)\s+(?:below|under|beneath)\s+(\d+(?:\.\d+)?)'
            ],
            "rejection": [
                r'\b(?:rejection|reject|rejecting)\s+(?:near|at|around)\s+(\d+(?:\.\d+)?)',
                r'\[REJECTION\].*?(?:near|at|around)\s+(\d+(?:\.\d+)?)'
            ],
            "bounce": [
                r'\b(?:bounce|bouncing|support)\s+(?:from|off|at)\s+(\d+(?:\.\d+)?)',
                r'\[BOUNCE\].*?(?:from|off|at)\s+(\d+(?:\.\d+)?)'
            ]
        }
        
        # Bias extraction patterns
        self.bias_patterns = [
            r'(?i)(?:remain|bias|sentiment|outlook|stance)\s+(bullish|bearish)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)',
            r'(?i)(bullish|bearish)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)',
            r'(?i)(bullish|bearish)\s+(?:bias|sentiment|outlook|stance)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)'
        ]
        
        # Bias flip patterns
        self.flip_patterns = [
            r'(?i)(?:flip|switch|turn|change)\s+(?:to)?\s+(bullish|bearish)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)',
            r'(?i)(?:above|below|over|under)\s+(\d+(?:\.\d+)?)\s+(?:flip|switch|turn|change)\s+(?:to)?\s+(bullish|bearish)',
            r'(?i)(bullish|bearish)\s+(?:on|if|when)\s+(?:above|below|over|under)\s+(\d+(?:\.\d+)?)' 
        ]
        
        # Target extraction patterns
        self.target_patterns = [
            r'(?i)(?:target|tgt|price target|take profit|tp)(?:\s+\d+)?:\s*(\d+(?:\.\d+)?)',
            r'(?i)(?:target|tgt|price target|take profit|tp)(?:\s+\d+)?\s+(?:at|is|of|near|around)?\s*(\d+(?:\.\d+)?)',
            r'(?i)(?:target|tgt|price target|take profit|tp)(?:\s+\d+)?[:\s]+(\d+(?:\.\d+)?)'
        ]
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by replacing emojis with standard text markers.
        
        Args:
            text: Raw text with potential emojis
            
        Returns:
            Normalized text with emojis replaced by standard markers
        """
        normalized = text
        for emoji, replacement in self.emoji_map.items():
            normalized = normalized.replace(emoji, replacement)
        return normalized
    
    def extract_ticker_symbols(self, text: str) -> List[str]:
        """
        Extract ticker symbols from text.
        
        Args:
            text: The text to extract ticker symbols from
            
        Returns:
            List of ticker symbols found in the text
        """
        ticker_matches = re.findall(self.ticker_pattern, text)
        # Remove common words that might be mistaken for tickers
        excluded_words = {"A", "I", "AT", "BE", "DO", "GO", "IF", "IN", "IS", "IT", "OR", "TO", "BY", "ON", "FOR", "THE"}
        tickers = [ticker for ticker in ticker_matches if ticker not in excluded_words]
        
        logger.info(f"Extracted {len(tickers)} ticker symbols: {tickers}")
        return tickers
    
    def extract_ticker_sections(self, text: str) -> Dict[str, str]:
        """
        Extract sections of text corresponding to different ticker symbols.
        
        Args:
            text: The text to extract ticker sections from
            
        Returns:
            Dictionary mapping ticker symbols to their sections of text
        """
        normalized_text = self.normalize_text(text)
        
        # Try different section extraction patterns
        for format_name, pattern in self.section_patterns.items():
            sections = re.findall(pattern, normalized_text)
            if sections:
                logger.debug(f"Found {len(sections)} ticker sections using pattern: {pattern}")
                return {ticker: content for ticker, content in sections}
        
        # Fallback: Try to split based on common patterns
        fallback_sections = {}
        tickers = self.extract_ticker_symbols(normalized_text)
        
        for ticker in tickers:
            # Look for ticker followed by a section of text
            ticker_pattern = rf'(?ms)(?:^|\n)({ticker})(?::|$|\n)([^A-Z]+)(?=\n[A-Z]{{1,5}}(?::|$|\n)|\Z)'
            matches = re.findall(ticker_pattern, normalized_text)
            
            if matches:
                for t, content in matches:
                    fallback_sections[t] = content.strip()
        
        return fallback_sections
    
    def extract_signals(self, ticker: str, text: str) -> List[SignalDTO]:
        """
        Extract trading signals from text for a specific ticker.
        
        Args:
            ticker: The ticker symbol
            text: The text section for this ticker
            
        Returns:
            List of Signal objects
        """
        signals = []
        
        # Process each signal category
        for category, patterns in self.signal_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Convert the price level to float
                        price_level = float(match)
                        
                        # Determine comparison type and category
                        comparison = ComparisonTypeDTO.ABOVE
                        if category == "breakout":
                            signal_category = SignalCategoryDTO.BREAKOUT
                            comparison = ComparisonTypeDTO.ABOVE
                        elif category == "breakdown":
                            signal_category = SignalCategoryDTO.BREAKDOWN
                            comparison = ComparisonTypeDTO.BELOW
                        elif category == "rejection":
                            signal_category = SignalCategoryDTO.REJECTION
                            comparison = ComparisonTypeDTO.NEAR
                        elif category == "bounce":
                            signal_category = SignalCategoryDTO.BOUNCE
                            comparison = ComparisonTypeDTO.ABOVE
                        else:
                            continue
                        
                        # Extract targets for this signal
                        targets = self.extract_targets(text)
                        if not targets:
                            # If no targets found in full text, look for numbers that might be targets
                            numbers = re.findall(r'(?<!\.)(?<!\d)\d+(?:\.\d+)?(?!\d)(?!\.)', text)
                            if numbers and len(numbers) > 1:
                                targets = {price_level}  # Default to the trigger price
                        
                        # Create the signal object
                        signal = SignalDTO(
                            category=signal_category,
                            comparison=comparison,
                            trigger=price_level,
                            targets=targets or {price_level},  # Default to the trigger price
                            aggressiveness=AggressivenessDTO.NONE
                        )
                        
                        signals.append(signal)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error extracting signal for {ticker}: {e}")
        
        return signals
    
    def extract_bias(self, ticker: str, text: str) -> Optional[BiasDTO]:
        """
        Extract market bias from text for a specific ticker.
        
        Args:
            ticker: The ticker symbol
            text: The text section for this ticker
            
        Returns:
            Bias object if found, None otherwise
        """
        # Extract bias from text
        for pattern in self.bias_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Format might be (direction, price) or (price, direction) depending on regex
                    if len(match) == 2:
                        if match[0].lower() in ["bullish", "bearish"]:
                            direction_str, price_str = match
                        else:
                            price_str, direction_str = match
                    
                        # Parse direction
                        if direction_str.lower() == "bullish":
                            direction = BiasDirectionDTO.BULLISH
                        elif direction_str.lower() == "bearish":
                            direction = BiasDirectionDTO.BEARISH
                        else:
                            continue
                        
                        # Parse price
                        price = float(price_str)
                        
                        # Determine condition type based on context
                        condition_text = re.search(r'(above|below|near)\s+\d+(?:\.\d+)?', text, re.IGNORECASE)
                        if condition_text:
                            condition_str = condition_text.group(1).lower()
                            if condition_str == "above":
                                condition = ComparisonTypeDTO.ABOVE
                            elif condition_str == "below":
                                condition = ComparisonTypeDTO.BELOW
                            else:
                                condition = ComparisonTypeDTO.NEAR
                        else:
                            # Default condition based on direction
                            condition = ComparisonTypeDTO.ABOVE if direction == BiasDirectionDTO.BULLISH else ComparisonTypeDTO.BELOW
                        
                        # Create bias object
                        bias = BiasDTO(
                            direction=direction,
                            condition=condition,
                            price=price
                        )
                        
                        # Extract potential bias flip
                        bias_flip = self.extract_bias_flip(text)
                        if bias_flip:
                            bias.flip = bias_flip
                        
                        return bias
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error extracting bias for {ticker}: {e}")
        
        return None
    
    def extract_bias_flip(self, text: str) -> Optional[BiasFlipDTO]:
        """
        Extract bias flip conditions from text.
        
        Args:
            text: The text to extract bias flip from
            
        Returns:
            BiasFlip object if found, None otherwise
        """
        for pattern in self.flip_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Format might be (direction, price) or (price, direction) depending on regex
                    if len(match) == 2:
                        if match[0].lower() in ["bullish", "bearish"]:
                            direction_str, price_str = match
                        else:
                            price_str, direction_str = match
                    
                        # Parse direction
                        if direction_str.lower() == "bullish":
                            direction = BiasDirectionDTO.BULLISH
                        elif direction_str.lower() == "bearish":
                            direction = BiasDirectionDTO.BEARISH
                        else:
                            continue
                        
                        # Parse price
                        price = float(price_str)
                        
                        # Create bias flip object
                        return BiasFlipDTO(
                            direction=direction,
                            price_level=price
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error extracting bias flip: {e}")
        
        return None
    
    def extract_targets(self, text: str) -> Set[float]:
        """
        Extract price targets from text.
        
        Args:
            text: The text to extract targets from
            
        Returns:
            Set of target prices
        """
        targets = set()
        
        # Extract targets using various patterns
        for pattern in self.target_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    target = float(match)
                    targets.add(target)
                except (ValueError, TypeError):
                    pass
        
        # Process line by line for targets with numbers
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and any(kw in line.lower() for kw in ['target', 'tgt', 't:', 'price target', 'take profit', 'tp']):
                # Just extract numbers from target line
                numbers = re.findall(r'(?<!\.)(?<!\d)\d+(?:\.\d+)?(?!\d)(?!\.)', line)
                for num in numbers:
                    try:
                        target = float(num)
                        targets.add(target)
                    except (ValueError, TypeError):
                        pass
        
        return targets
    
    def process_ticker_sections(self, sections: Dict[str, str]) -> List[TickerSetupDTO]:
        """
        Process ticker sections to extract signals and biases.
        
        Args:
            sections: Dictionary mapping ticker symbols to their sections of text
            
        Returns:
            List of TickerSetup objects
        """
        ticker_setups = []
        
        for ticker, section_text in sections.items():
            # Extract signals
            signals = self.extract_signals(ticker, section_text)
            
            # Extract bias
            bias = self.extract_bias(ticker, section_text)
            
            # Only create setup if we have signals or bias
            if signals or bias:
                setup = TickerSetupDTO(
                    symbol=ticker,
                    signals=signals,
                    bias=bias,
                    text=section_text.strip()
                )
                ticker_setups.append(setup)
                logger.debug(f"Created setup for {ticker} with {len(signals)} signals and bias={bias is not None}")
        
        return ticker_setups
    
    def parse_message(self, text: str, message_date: Optional[date] = None, source: str = "unknown") -> Optional[TradeSetupDTO]:
        """
        Parse a setup message text into a structured TradeSetupDTO object.
        
        Args:
            text: The raw setup message text
            message_date: The date of the setup message, defaults to today
            source: Source of the message, defaults to 'unknown'
            
        Returns:
            TradeSetupDTO object if parsing successful, None otherwise
        """
        if not text or not text.strip():
            return None
        
        # Use today's date if not provided
        current_date = datetime.now().date()
        effective_date = message_date if message_date else current_date
        
        # Find potential ticker symbols in the message
        ticker_symbols = self.extract_ticker_symbols(text)
        if not ticker_symbols:
            return None
        
        # Try to extract ticker sections
        ticker_sections = self.extract_ticker_sections(text)
        
        # If we found sections, process each section
        if ticker_sections:
            ticker_setups = self.process_ticker_sections(ticker_sections)
            logger.info(f"Found {len(ticker_setups)} ticker setups using section-based approach")
        else:
            # Fallback: Try simpler approach for single ticker
            ticker = ticker_symbols[0]
            signals = self.extract_signals(ticker, text)
            bias = self.extract_bias(ticker, text)
            
            if signals or bias:
                ticker_setups = [TickerSetupDTO(
                    symbol=ticker,
                    signals=signals,
                    bias=bias,
                    text=text
                )]
                logger.info(f"Found 1 ticker setup using fallback approach")
            else:
                ticker_setups = []
        
        # Only create the message if we found some ticker setups
        if ticker_setups:
            # Create the setup message
            setup_message = TradeSetupDTO(
                raw_text=text,
                date=message_date,
                source=source,
                setups=ticker_setups,
                created_at=datetime.now()
            )
            return setup_message
        
        return None