"""
Trade Setup Parser Module

This module is responsible for parsing A+ Trade Setup messages into structured data.
It extracts ticker symbols, signals, price levels, and bias information.
"""
import re
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Union, Match

from common.models import (
    TradeSetupMessage, 
    TickerSetup, 
    Signal, 
    Bias, 
    BiasFlip, 
    SignalCategory, 
    ComparisonType, 
    Aggressiveness,
    BiasDirection
)

logger = logging.getLogger(__name__)

# Regular expression patterns
DATE_PATTERN = r"A\+ Trade Setups[^\n]*(?:[—–-]|\s+)(\w{3}\s+\w{3}\s+\d{1,2})|A\+ Trade Setups \((\w{3}, \w{3} \d{1,2})\)"
TICKER_PATTERN = r"(?:\d+\)\s+|—{2,}[\r\n]+)([A-Z]+)"

# Emoji patterns - traditional format
EMOJI_BREAKOUT_PATTERN = r"🔼\s+(?:(Aggressive|Conservative)\s+(?:Long|Breakout)|Breakout|Breakout Entry|Breakout Entries)\s+(?:Above|Over)\s+(\d+\.\d+)"
EMOJI_BREAKDOWN_PATTERN = r"🔻\s+(?:(Aggressive|Conservative)\s+(?:Short|Breakdown)|Breakdown|Breakdown Entry|Breakdown Entries)\s+(?:Below|Under)\s+(\d+\.\d+)|🔻\s+(?:Breakdown|Breakdown Entry|Breakdown Entries)\s+(?:(Aggressive|Conservative))?\s*(?:Below|Under)\s+(\d+\.\d+)"
EMOJI_REJECTION_PATTERN = r"❌\s+(?:Rejection|Rejection Short|Rejection Short Zone|Rejection Short Zones|Rejection Levels)(?:\s+(?:Near|at|levels|level))?\s+(\d+\.\d+)"
EMOJI_BOUNCE_PATTERN = r"🔄\s+(?:Bounce|Bounce From|Bounce Entry|Bounce Long Zones|Bounce Zone)\s+(?:From|Near)?\s+(\d+\.\d+)"
EMOJI_BOUNCE_ZONE_PATTERN = r"🌀\s+(?:Bounce Zone|Bounce Long Zones)(?:\s+Near)?\s+(?:(\d+\.\d+)[-–](\d+\.\d+)|(\d+\.\d+))"
EMOJI_TARGET_PATTERN = r"(?:🔼|🔻|Targets:|Target:)\s*(?:(\d+\.\d+)(?:,\s*|-)?)+"
EMOJI_BIAS_PATTERN = r"⚠️.*?(Bullish|Bearish)[^0-9.,\n]*(?:above|below|under|over|while holding above|while holding below|holds?|holding|momentum)\s+(\d+\.\d+)"

# Text-based patterns - newer format
TEXT_BREAKOUT_PATTERN = r"(?:Breakout|Breakout Entry|Long)\s+(?:Above|Over)\s+(\d+\.\d+)"
TEXT_BREAKDOWN_PATTERN = r"(?:Breakdown|Breakdown Entry|Short)\s+(?:Below|Under)\s+(\d+\.\d+)"
TEXT_REJECTION_PATTERN = r"(?:Rejection|Rejection\s+Near|Rejection at)\s+(\d+\.\d+)"
TEXT_BOUNCE_PATTERN = r"(?:Bounce|Bounce From|Bounce Near)\s+(\d+\.\d+)"
TEXT_TARGET_PATTERN = r"Target\s+\d+:\s+(\d+\.\d+)"
TEXT_BIAS_PATTERN = r"(Bullish|Bearish)\s+bias\s+(?:above|below|under|over)\s+(\d+\.\d+)"
TEXT_BIAS_FLIP_PATTERN = r"(?:flips|flip to|flips?)\s+(bullish|bearish)\s+(?:above|below|under|over)\s+(\d+\.\d+)"

# Combined patterns - we'll try both emoji and text versions
BREAKOUT_PATTERN = f"({EMOJI_BREAKOUT_PATTERN}|{TEXT_BREAKOUT_PATTERN})"
BREAKDOWN_PATTERN = f"({EMOJI_BREAKDOWN_PATTERN}|{TEXT_BREAKDOWN_PATTERN})"
REJECTION_PATTERN = f"({EMOJI_REJECTION_PATTERN}|{TEXT_REJECTION_PATTERN})"
BOUNCE_PATTERN = f"({EMOJI_BOUNCE_PATTERN}|{TEXT_BOUNCE_PATTERN})"
BOUNCE_ZONE_PATTERN = EMOJI_BOUNCE_ZONE_PATTERN  # Keep as is for now
TARGET_PATTERN = f"({EMOJI_TARGET_PATTERN}|{TEXT_TARGET_PATTERN})"
BIAS_PATTERN = f"({EMOJI_BIAS_PATTERN}|{TEXT_BIAS_PATTERN})"
BIAS_FLIP_PATTERN = r"(?:flips|flip to|flips?) (bullish|bearish)(?:[^0-9.,\n]*)(?:on|if|when|above|below|over|under|cross|breaks?|only)[^0-9.,\n]*(\d+\.\d+)"

# Month name mapping
MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}


def parse_date(date_str: str) -> date:
    """Parse date from various formats like 'Wed May 14'."""
    try:
        parts = date_str.strip().split()
        if len(parts) == 3:
            _, month, day = parts
            month_num = MONTH_MAP.get(month[:3], 1)  # Default to January if not found
            day_num = int(day)
            year = datetime.now().year
            return date(year, month_num, day_num)
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {str(e)}")
    
    # Fallback to current date
    return date.today()


def extract_numbers(text: str, pattern: str = r"\d+\.\d+") -> List[float]:
    """Extract float numbers from text using a given pattern."""
    return [float(match) for match in re.findall(pattern, text)]


def extract_targets(text: str, signal_line: str) -> List[float]:
    """Extract target price levels for a signal."""
    # First try the explicit target pattern
    targets_match = re.search(TARGET_PATTERN, text)
    if targets_match:
        return extract_numbers(targets_match.group(0))
    
    # If not found, try to extract numbers from the signal line itself
    # Usually targets are listed after the trigger price
    numbers = extract_numbers(signal_line)
    return numbers[1:] if len(numbers) > 1 else []


def extract_signals(text: str, symbol: str) -> List[Signal]:
    """Extract all signals for a ticker symbol."""
    signals = []
    lines = text.split('\n')
    
    # Find range for this symbol
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if re.search(rf"\b{symbol}\b", line) or re.search(r"\d+\)\s+" + symbol, line):
            start_idx = i
        # Check for next ticker or end of message
        if start_idx is not None and i > start_idx and (
            re.search(r"\d+\)\s+[A-Z]+", line) or 
            re.search(r"^[A-Z]+\s*$", line) or
            re.search(r"@everyone", line)
        ):
            end_idx = i
            break
    
    if start_idx is None:
        return []
    
    if end_idx is None:
        end_idx = len(lines)
    
    ticker_text = "\n".join(lines[start_idx:end_idx])
    
    # Extract breakouts
    for line in ticker_text.split('\n'):
        breakout_match = re.search(BREAKOUT_PATTERN, line)
        if breakout_match:
            # Handle aggressiveness indicator if present
            aggressiveness_str = breakout_match.group(1) if breakout_match.group(1) else "none"
            
            # Get the trigger price (always group 2 in the simplified pattern)
            trigger_price = float(breakout_match.group(2))
            
            aggressiveness = (Aggressiveness.AGGRESSIVE if aggressiveness_str and aggressiveness_str.lower() == "aggressive" else
                             Aggressiveness.CONSERVATIVE if aggressiveness_str and aggressiveness_str.lower() == "conservative" else
                             Aggressiveness.NONE)
            
            targets = extract_targets(ticker_text, line)
            
            signals.append(Signal(
                category=SignalCategory.BREAKOUT,
                aggressiveness=aggressiveness,
                comparison=ComparisonType.ABOVE,
                trigger=trigger_price,
                targets=targets
            ))
    
    # Extract breakdowns
    for line in ticker_text.split('\n'):
        breakdown_match = re.search(BREAKDOWN_PATTERN, line)
        if breakdown_match:
            # We have two different pattern formats possible:
            # 1. "Aggressive Short Below XX.XX"
            # 2. "Breakdown Below XX.XX"
            
            # Check which format matched
            if breakdown_match.group(1) and breakdown_match.group(2):
                # Format: "Aggressive Short Below XX.XX"
                aggressiveness_str = breakdown_match.group(1)
                trigger_price = float(breakdown_match.group(2))
            else:
                # Format: "Breakdown (Aggressive) Below XX.XX"
                aggressiveness_str = breakdown_match.group(3) if breakdown_match.group(3) else "none"
                trigger_price = float(breakdown_match.group(4) or 0)
            
            aggressiveness = (Aggressiveness.AGGRESSIVE if aggressiveness_str and aggressiveness_str.lower() == "aggressive" else
                             Aggressiveness.CONSERVATIVE if aggressiveness_str and aggressiveness_str.lower() == "conservative" else
                             Aggressiveness.NONE)
            
            targets = extract_targets(ticker_text, line)
            
            signals.append(Signal(
                category=SignalCategory.BREAKDOWN,
                aggressiveness=aggressiveness,
                comparison=ComparisonType.BELOW,
                trigger=trigger_price,
                targets=targets
            ))
    
    # Extract rejections
    for line in ticker_text.split('\n'):
        rejection_match = re.search(REJECTION_PATTERN, line)
        if rejection_match:
            trigger_price = float(rejection_match.group(1))
            targets = extract_targets(ticker_text, line)
            
            signals.append(Signal(
                category=SignalCategory.REJECTION,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.NEAR,
                trigger=trigger_price,
                targets=targets
            ))
    
    # Extract bounces
    for line in ticker_text.split('\n'):
        bounce_match = re.search(BOUNCE_PATTERN, line)
        if bounce_match:
            trigger_price = float(bounce_match.group(1))
            targets = extract_targets(ticker_text, line)
            
            signals.append(Signal(
                category=SignalCategory.BOUNCE,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.NEAR,
                trigger=trigger_price,
                targets=targets
            ))
    
    # Extract bounce zones
    for line in ticker_text.split('\n'):
        bounce_zone_match = re.search(BOUNCE_ZONE_PATTERN, line)
        if bounce_zone_match:
            if bounce_zone_match.group(1) and bounce_zone_match.group(2):
                # Range format
                lower = float(bounce_zone_match.group(1))
                upper = float(bounce_zone_match.group(2))
                trigger = [lower, upper]
            else:
                # Single price
                trigger = float(bounce_zone_match.group(3))
            
            targets = extract_targets(ticker_text, line)
            
            signals.append(Signal(
                category=SignalCategory.BOUNCE,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.RANGE if isinstance(trigger, list) else ComparisonType.NEAR,
                trigger=trigger,
                targets=targets
            ))
    
    # Fallback for bounce zone pattern with simpler regex if no signals found
    if not signals:
        # Look for "bounce zone" text with nearby numbers
        bounce_lines = [line for line in ticker_text.split('\n') if 'bounce zone' in line.lower() or 'bounce from' in line.lower()]
        for line in bounce_lines:
            numbers = extract_numbers(line)
            if numbers:
                if len(numbers) >= 2:
                    # Multiple numbers may indicate a range
                    signals.append(Signal(
                        category=SignalCategory.BOUNCE,
                        aggressiveness=Aggressiveness.NONE,
                        comparison=ComparisonType.RANGE,
                        trigger=[numbers[0], numbers[1]],
                        targets=numbers[2:] if len(numbers) > 2 else []
                    ))
                else:
                    signals.append(Signal(
                        category=SignalCategory.BOUNCE,
                        aggressiveness=Aggressiveness.NONE,
                        comparison=ComparisonType.NEAR,
                        trigger=numbers[0],
                        targets=[]
                    ))
    
    # Check for Aggressive Long or Aggressive Short as fallback patterns
    if not signals:
        aggressive_long = re.search(r"(?i)aggressive\s+long.*?(\d+\.\d+)", ticker_text)
        if aggressive_long:
            signals.append(Signal(
                category=SignalCategory.BREAKOUT,
                aggressiveness=Aggressiveness.AGGRESSIVE,
                comparison=ComparisonType.ABOVE,
                trigger=float(aggressive_long.group(1)),
                targets=extract_numbers(ticker_text)
            ))
        
        aggressive_short = re.search(r"(?i)aggressive\s+short.*?(\d+\.\d+)", ticker_text)
        if aggressive_short:
            signals.append(Signal(
                category=SignalCategory.BREAKDOWN,
                aggressiveness=Aggressiveness.AGGRESSIVE,
                comparison=ComparisonType.BELOW,
                trigger=float(aggressive_short.group(1)),
                targets=extract_numbers(ticker_text)
            ))
    
    return signals


def extract_bias(text: str, symbol: str) -> Optional[Bias]:
    """Extract bias information for a ticker symbol."""
    lines = text.split('\n')
    
    # First look for the newer structured format
    ticker_section_start = None
    ticker_section_end = None
    
    # Try to find the ticker section using numbered format: "1) SPY:"
    for i, line in enumerate(lines):
        # Match section headers like "1) SPY:" or "2. MSFT:"
        if re.search(rf"\d+\)?\.?\s+{symbol}:", line):
            ticker_section_start = i
            
            # Find where this section ends (next ticker or end of text)
            ticker_section_end = len(lines)
            for j in range(i + 1, len(lines)):
                if re.search(r"\d+\)?\.?\s+[A-Z]+:", lines[j]):
                    ticker_section_end = j
                    break
            
            break
    
    # If we didn't find a section with numbered format, try the traditional format
    if ticker_section_start is None:
        for i, line in enumerate(lines):
            if re.search(rf"\b{symbol}\b", line) or re.search(r"\b{symbol}$", line.strip()):
                ticker_section_start = i
                
                # Find where this section ends
                ticker_section_end = len(lines)
                for j in range(i + 1, len(lines)):
                    if (re.search(r"\b[A-Z]{2,5}\b", lines[j]) and 
                        not re.search(rf"\b{symbol}\b", lines[j]) and
                        not "resistance" in lines[j].lower() and
                        not "support" in lines[j].lower()):
                        ticker_section_end = j
                        break
                
                break
    
    # If we still didn't find a section, we can't extract bias
    if ticker_section_start is None:
        return None
    
    # Make sure we have an end index
    if ticker_section_end is None:
        ticker_section_end = len(lines)
    
    # Get the section text
    ticker_section = lines[ticker_section_start:ticker_section_end]
    ticker_text = "\n".join(ticker_section)
    
    # Try to find structured bias formats first
    structured_bias_regex = r"(?:^|\s+)-?\s*(Bullish|Bearish)\s+bias\s+(above|below)\s+(\d+\.\d+)"
    structured_bias_match = re.search(structured_bias_regex, ticker_text, re.IGNORECASE)
    
    if structured_bias_match:
        try:
            direction_str = structured_bias_match.group(1).lower()
            comparison_str = structured_bias_match.group(2).lower()
            price = float(structured_bias_match.group(3))
            
            direction = BiasDirection.BULLISH if direction_str == "bullish" else BiasDirection.BEARISH
            comparison = ComparisonType.ABOVE if comparison_str == "above" else ComparisonType.BELOW
            
            # Check for bias flip info
            flip_match = re.search(r"flips?\s+(bullish|bearish)\s+(above|below|at)\s+(\d+\.\d+)", 
                                ticker_text, re.IGNORECASE)
            flip = None
            if flip_match:
                flip_direction_str = flip_match.group(1).lower()
                flip_price = float(flip_match.group(3))
                flip_direction = BiasDirection.BULLISH if flip_direction_str == "bullish" else BiasDirection.BEARISH
                
                flip = BiasFlip(
                    direction=flip_direction,
                    price_level=flip_price
                )
            
            return Bias(
                direction=direction,
                condition=comparison,
                price=price,
                flip=flip
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing structured bias: {str(e)}")
            # Continue to try other formats
    
    # Traditional bias extraction if structured format fails
    # First try with specific pattern from constants
    bias_match = re.search(BIAS_PATTERN, ticker_text)
    
    # If that fails, try with a more lenient pattern
    if not bias_match:
        # Look for any line containing bullish/bearish
        lenient_pattern = r"(?i)(bullish|bearish)[^0-9.]*?(\d+\.\d+)"
        bias_match = re.search(lenient_pattern, ticker_text)
        
        if not bias_match:
            # Even more lenient, just look for the words with numbers
            for line in ticker_text.split('\n'):
                if ('bullish' in line.lower() or 'bearish' in line.lower()) and re.search(r"\d+\.\d+", line):
                    direction_str = 'bullish' if 'bullish' in line.lower() else 'bearish'
                    numbers = extract_numbers(line)
                    if numbers:
                        # Create a custom match object with a group method
                        class MockMatch:
                            def group(self, n):
                                if n == 0:
                                    return line
                                elif n == 1:
                                    return direction_str
                                elif n == 2:
                                    return str(numbers[0])
                                else:
                                    return None
                        
                        bias_match = MockMatch()
                        break
    
    if not bias_match:
        return None
    
    # Safety checks for the match
    if not bias_match.group(1) or not bias_match.group(2):
        logger.warning(f"Invalid bias match: {bias_match.group(0)}")
        return None
    
    try:
        direction_str = bias_match.group(1).lower()
        direction = BiasDirection.BULLISH if direction_str == "bullish" else BiasDirection.BEARISH
        price = float(bias_match.group(2))
        
        # Determine comparison type from context
        match_text = bias_match.group(0).lower() if hasattr(bias_match.group(0), 'lower') else ""
        comparison = ComparisonType.ABOVE
        if "below" in match_text or "under" in match_text:
            comparison = ComparisonType.BELOW
        
        return Bias(
            direction=direction,
            condition=comparison,
            price=price,
            flip=None  # No flip information from traditional format
        )
    except (TypeError, ValueError) as e:
        logger.warning(f"Error parsing bias: {str(e)}")
        return None



def extract_tickers(text: str) -> List[str]:
    """Extract ticker symbols from the message."""
    tickers = []
    
    # Look for numbered tickers with parenthesis (1) SPY:)
    numbered_tickers_paren = re.findall(r"\d+\)\s+([A-Z]+)(?:\s*:|$)", text)
    if numbered_tickers_paren:
        tickers.extend(numbered_tickers_paren)
    
    # Look for numbered tickers with periods (1. SPY:)
    numbered_tickers_period = re.findall(r"\d+\.\s+([A-Z]+)(?:\s*:|$)", text)
    if numbered_tickers_period:
        tickers.extend(numbered_tickers_period)
    
    # Look for general numbered format with ticker and colon
    general_numbered = re.findall(r"^\s*\d+[.)]?\s+([A-Z]+):", text, re.MULTILINE)
    if general_numbered:
        for ticker in general_numbered:
            if ticker not in tickers:
                tickers.append(ticker)
    
    # Look for section headers
    section_tickers = re.findall(r"^([A-Z]+)$", text, re.MULTILINE)
    if section_tickers:
        for ticker in section_tickers:
            if ticker not in tickers and len(ticker) >= 2 and ticker != "A+":
                tickers.append(ticker)
    
    # Look for divider sections
    divider_tickers = re.findall(r"—{2,}[\r\n]+([A-Z]+)", text)
    if divider_tickers:
        for ticker in divider_tickers:
            if ticker not in tickers:
                tickers.append(ticker)
    
    # Look for signal emoji patterns
    emoji_patterns = [
        r"^(?:🔼|🔻|❌|🔄|🌀)\s+(?:[A-Za-z]+\s+)+([A-Z]+)",  # Emoji followed by signal text and ticker
        r"([A-Z]+)\s*\n+\s*(?:🔼|🔻|❌|🔄|🌀)"  # Ticker followed by emoji on next line
    ]
    
    for pattern in emoji_patterns:
        emoji_tickers = re.findall(pattern, text, re.MULTILINE)
        if emoji_tickers:
            for ticker in emoji_tickers:
                if ticker not in tickers and len(ticker) >= 2 and ticker != "A+":
                    tickers.append(ticker)
    
    # Debug - if no tickers found, try a more lenient approach
    if not tickers:
        logger.debug("No tickers found with standard patterns, trying lenient approach")
        
        # Look for any standalone uppercase words that could be tickers
        lines = text.split('\n')
        in_ticker_section = False
        current_section = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check for standalone ticker (all caps, 2-5 letters)
            if re.match(r"^[A-Z]{2,5}$", line):
                ticker = line
                if ticker not in tickers and ticker != "A+" and ticker != "PM":
                    tickers.append(ticker)
                in_ticker_section = True
                current_section = [ticker]
                continue
                
            # Check for ticker: format
            ticker_match = re.match(r"^([A-Z]{2,5}):", line)
            if ticker_match:
                ticker = ticker_match.group(1)
                if ticker not in tickers and ticker != "A+" and ticker != "PM":
                    tickers.append(ticker)
                in_ticker_section = True
                current_section = [ticker]
                continue
    
    return tickers


def extract_structured_signals(text: str, symbol: str) -> List[Signal]:
    """
    Extract signals from structured message format.
    
    This function is specifically designed to parse the newer format with numbered tickers
    and structured indented information.
    
    Args:
        text: The raw message text
        symbol: The ticker symbol to extract signals for
        
    Returns:
        List[Signal]: List of extracted signals
    """
    signals = []
    lines = text.split('\n')
    logger.debug(f"Extracting structured signals for {symbol} from message with {len(lines)} lines")
    
    # Find the section for this ticker
    ticker_section_start = None
    ticker_section_end = None
    
    # Try pattern 1: Look for: "1) SPY: Breakdown Below 500.5"
    for i, line in enumerate(lines):
        # Match format like: "1) SPY: Breakdown Below 500.5"
        header_match = re.search(fr"\d+\)?\s+{symbol}:", line)
        
        if header_match:
            ticker_section_start = i
            
            # Find the end of this section (next ticker or end of text)
            ticker_section_end = len(lines)
            for j in range(i + 1, len(lines)):
                # Next section starts with a digit followed by ")" and a ticker
                if re.search(r"\d+\)?\s+[A-Z]+:", lines[j]):
                    ticker_section_end = j
                    break
            
            # Extract the section
            section_lines = lines[ticker_section_start:ticker_section_end]
            section_text = "\n".join(section_lines)
            
            # Look for signal type in the section header
            first_line = section_lines[0]
            signal_match = re.search(r"(Breakout|Breakdown|Rejection|Bounce)\s+(Above|Below|Near|From)\s+(\d+\.\d+)", first_line)
            
            if signal_match:
                signal_type = signal_match.group(1).lower()
                comparison_word = signal_match.group(2).lower()
                trigger_price = float(signal_match.group(3))
                
                # Extract targets from Target lines
                targets = []
                target_pattern = re.compile(r"Target\s+\d+:\s+(\d+\.\d+)")
                for section_line in section_lines:
                    target_match = target_pattern.search(section_line)
                    if target_match:
                        targets.append(float(target_match.group(1)))
                
                # Try alternative formats if no targets found
                if not targets:
                    for section_line in section_lines:
                        if "target" in section_line.lower():
                            numbers = extract_numbers(section_line)
                            if len(numbers) > 0:
                                targets = numbers
                                break
                
                # Check for support/resistance values to use as targets if still no targets found
                if not targets:
                    # Look for resistance or support values
                    for section_line in section_lines:
                        resistance_match = re.search(r"Resistance:\s+(\d+\.\d+)", section_line)
                        if resistance_match:
                            price = float(resistance_match.group(1))
                            # Use resistance as the trigger for breakdowns and rejections
                            if "breakdown" in signal_type or "rejection" in signal_type:
                                trigger_price = price
                        
                        support_match = re.search(r"Support:\s+(\d+\.\d+)", section_line)
                        if support_match:
                            price = float(support_match.group(1))
                            # Use support as the trigger for breakouts and bounces
                            if "breakout" in signal_type or "bounce" in signal_type:
                                trigger_price = price
                
                # Determine signal category and comparison type
                if "breakout" in signal_type:
                    category = SignalCategory.BREAKOUT
                    comparison = ComparisonType.ABOVE
                elif "breakdown" in signal_type:
                    category = SignalCategory.BREAKDOWN
                    comparison = ComparisonType.BELOW
                elif "rejection" in signal_type:
                    category = SignalCategory.REJECTION
                    comparison = ComparisonType.NEAR
                elif "bounce" in signal_type:
                    category = SignalCategory.BOUNCE
                    comparison = ComparisonType.NEAR
                else:
                    # Default fallback
                    category = SignalCategory.BREAKOUT
                    comparison = ComparisonType.ABOVE
                
                # Create the signal
                signals.append(Signal(
                    category=category,
                    aggressiveness=Aggressiveness.NONE,  # Can enhance this later
                    comparison=comparison,
                    trigger=trigger_price,
                    targets=targets
                ))
            
            # Once found, we can break the search loop
            break
    
    # If no signals found but we have a ticker section, look for context clues
    if not signals and ticker_section_start is not None and ticker_section_end is not None:
        section_lines = lines[ticker_section_start:ticker_section_end]
        section_text = "\n".join(section_lines)
        
        # Look for bias line which often contains the price level
        bias_match = re.search(r"(Bullish|Bearish)\s+bias\s+(above|below)\s+(\d+\.\d+)", section_text, re.IGNORECASE)
        if bias_match:
            bias_type = bias_match.group(1).lower()
            bias_comparison = bias_match.group(2).lower()
            price_level = float(bias_match.group(3))
            
            # Determine signal category and comparison based on bias
            if bias_type == "bullish" and bias_comparison == "above":
                category = SignalCategory.BREAKOUT
                comparison = ComparisonType.ABOVE
            elif bias_type == "bearish" and bias_comparison == "below":
                category = SignalCategory.BREAKDOWN
                comparison = ComparisonType.BELOW
            else:
                # Default
                category = SignalCategory.REJECTION
                comparison = ComparisonType.NEAR
            
            # Extract targets
            targets = []
            target_pattern = re.compile(r"Target\s+\d+:\s+(\d+\.\d+)")
            for section_line in section_lines:
                target_match = target_pattern.search(section_line)
                if target_match:
                    targets.append(float(target_match.group(1)))
            
            # Create a signal based on the bias
            signals.append(Signal(
                category=category,
                aggressiveness=Aggressiveness.NONE,
                comparison=comparison,
                trigger=price_level,
                targets=targets
            ))
    
    logger.debug(f"Extracted {len(signals)} structured signals for {symbol}")
    return signals


def parse_setup_message(text: str, source: str = "unknown") -> TradeSetupMessage:
    """
    Parse a complete A+ Trade Setup message.
    
    Args:
        text: The raw message text
        source: Source of the message (e.g., "discord", "email")
        
    Returns:
        TradeSetupMessage: Structured data representation of the message
    """
    # Extract date
    date_match = re.search(DATE_PATTERN, text)
    if date_match:
        # Handle both formats from DATE_PATTERN
        date_str = date_match.group(1) if date_match.group(1) else date_match.group(2)
        message_date = parse_date(date_str)
    else:
        message_date = date.today()
    
    # Extract tickers
    tickers = extract_tickers(text)
    logger.info(f"Extracted {len(tickers)} ticker symbols: {tickers}")
    
    # Process each ticker
    ticker_setups = []
    for symbol in tickers:
        logger.info(f"Processing ticker {symbol}")
        
        # First try structured signal extraction for newer format
        structured_signals = extract_structured_signals(text, symbol)
        
        # If that doesn't work, fall back to traditional extraction
        signals = structured_signals
        if not signals:
            logger.debug(f"No structured signals found for {symbol}, trying traditional extraction")
            signals = extract_signals(text, symbol)
        
        # Extract the ticker-specific text
        lines = text.split('\n')
        
        # Find range for this symbol (for bias extraction)
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if re.search(rf"\b{symbol}\b", line) or re.search(r"\d+\)\s+" + symbol, line):
                start_idx = i
            # Check for next ticker or end of message
            if start_idx is not None and i > start_idx and (
                re.search(r"\d+\)\s+[A-Z]+", line) or 
                re.search(r"^[A-Z]+\s*$", line) or
                re.search(r"@everyone", line)
            ):
                end_idx = i
                break
        
        ticker_text = ""
        if start_idx is not None:
            if end_idx is None:
                end_idx = len(lines)
            ticker_text = "\n".join(lines[start_idx:end_idx])
        
        # Extract bias
        bias = extract_bias(text, symbol)
        
        # Only add if we found signals or bias
        if signals or bias:
            logger.info(f"Found {len(signals)} signals and bias={bias is not None} for {symbol}")
            ticker_setups.append(TickerSetup(
                symbol=symbol,
                signals=signals,
                bias=bias,
                text=ticker_text or text  # Use ticker-specific text if available, otherwise full text
            ))
        else:
            logger.debug(f"No signals or bias found for {symbol}, skipping")
    
    # Create the complete message
    return TradeSetupMessage(
        date=message_date,
        raw_text=text,
        setups=ticker_setups,
        source=source,
        created_at=datetime.now()
    )