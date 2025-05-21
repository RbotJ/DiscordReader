"""
Enhanced Trade Setup Parser Module

This module provides advanced parsing functionality for trade setup messages,
extracting structured data with specific attention to:
- Ticker symbols
- Setup types (breakout, breakdown, rejection, bounce)
- Aggressiveness levels
- Price triggers and targets
- Bias conditions

The parser follows the specifications requested for the A+ Trading App.
"""

import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from enum import Enum, auto

# Configure logger
logger = logging.getLogger(__name__)

# Define enums for structured data
class SetupType(str, Enum):
    """Type of trading setup"""
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"

class Direction(str, Enum):
    """Direction of trading signal"""
    UP = "up"
    DOWN = "down"

class Aggressiveness(str, Enum):
    """Aggressiveness level of trading signal"""
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    NORMAL = "normal"

class BiasDirection(str, Enum):
    """Market bias direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"

# Define models using class-based approach
class SetupMessage:
    """Container for a complete setup message"""
    def __init__(self, id: Optional[int] = None, ticker: str = "", 
                 raw_text: str = "", timestamp: datetime = None, 
                 source: str = ""):
        self.id = id
        self.ticker = ticker
        self.raw_text = raw_text
        self.timestamp = timestamp or datetime.now()
        self.source = source
        self.signals = []
        self.bias = None
    
    def __repr__(self):
        return f"SetupMessage(ticker={self.ticker}, signals={len(self.signals)})"
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "raw_text": self.raw_text,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
            "signals": [signal.to_dict() for signal in self.signals],
            "bias": self.bias.to_dict() if self.bias else None
        }

class Signal:
    """Trading signal with trigger price and targets"""
    def __init__(self, id: Optional[int] = None, setup_id: Optional[int] = None,
                 type: str = "", direction: str = "", aggressiveness: Optional[str] = None,
                 trigger: float = 0.0, targets: List[float] = None,
                 confirmed: bool = False, confirmed_at: Optional[datetime] = None,
                 confirmation_details: Optional[Dict] = None):
        self.id = id
        self.setup_id = setup_id
        self.type = type
        self.direction = direction
        self.aggressiveness = aggressiveness
        self.trigger = trigger
        self.targets = targets or []
        self.confirmed = confirmed
        self.confirmed_at = confirmed_at
        self.confirmation_details = confirmation_details or {}
    
    def __repr__(self):
        return f"Signal(type={self.type}, direction={self.direction}, trigger={self.trigger})"
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "setup_id": self.setup_id,
            "type": self.type,
            "direction": self.direction,
            "aggressiveness": self.aggressiveness,
            "trigger": self.trigger,
            "targets": self.targets,
            "confirmed": self.confirmed,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "confirmation_details": self.confirmation_details
        }

class Bias:
    """Market bias information"""
    def __init__(self, id: Optional[int] = None, setup_id: Optional[int] = None,
                 direction: str = "", hold_level: float = 0.0,
                 breakdown_below: Optional[float] = None):
        self.id = id
        self.setup_id = setup_id
        self.direction = direction
        self.hold_level = hold_level
        self.breakdown_below = breakdown_below
    
    def __repr__(self):
        return f"Bias(direction={self.direction}, hold_level={self.hold_level})"
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "setup_id": self.setup_id,
            "direction": self.direction,
            "hold_level": self.hold_level,
            "breakdown_below": self.breakdown_below
        }

def parse_raw_setup_message(text: str) -> Tuple[SetupMessage, List[Signal], Optional[Bias]]:
    """
    Parse a raw setup message into structured data.
    
    Args:
        text: Raw message text
        
    Returns:
        Tuple containing (SetupMessage, List[Signal], Optional[Bias])
    """
    # Extract ticker symbol - first non-emoji line is usually the ticker
    lines = text.strip().split('\n')
    ticker = None
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        # Skip emoji-only lines
        if all(c in emoji_set for c in line.strip()):
            continue
        # Extract potential ticker from the beginning of the line
        match = re.match(r'^([A-Z]{1,5})\b', line.strip())
        if match:
            ticker = match.group(1)
            # Verify it's a reasonable ticker (not common words)
            if ticker not in {"A", "I", "AT", "BE", "DO", "GO", "IF", "IN", "IS", "IT", "OR", "TO"}:
                break
    
    if not ticker:
        # Fallback: scan for any ticker-like symbols
        ticker_matches = re.findall(r'\b[A-Z]{1,5}\b', text)
        filtered_tickers = [t for t in ticker_matches if t not in {"A", "I", "AT", "BE", "DO", "GO", "IF", "IN", "IS", "IT", "OR", "TO"}]
        if filtered_tickers:
            ticker = filtered_tickers[0]
        else:
            ticker = "UNKNOWN"
    
    # Create setup message
    setup_message = SetupMessage(
        ticker=ticker,
        raw_text=text,
        timestamp=datetime.now(),
        source="parsed"
    )
    
    # Extract signals
    signals = extract_signals_from_text(text, ticker)
    
    # Extract bias information
    bias = extract_bias_from_text(text, ticker)
    
    # Store in setup message
    setup_message.signals = signals
    setup_message.bias = bias
    
    return setup_message, signals, bias

def extract_signals_from_text(text: str, ticker: str) -> List[Signal]:
    """
    Extract trading signals from text.
    
    Args:
        text: Raw text
        ticker: Ticker symbol
        
    Returns:
        List of Signal objects
    """
    signals = []
    
    # Pattern for breakout signals
    breakout_patterns = [
        # Standard format: Aggressive/Conservative Breakout Above price (targets)
        r'(?:🔼|⬆️|🚀|🔝)?\s*(?P<agg>Aggressive|Conservative)?\s*(?:Breakout|Break out|Breaking out|Long)\s+(?:Above|Over|Past)\s+(?P<price>\d+(?:\.\d+)?)\s*(?:\((?P<targets>[^)]+)\))?',
        # Warning format: Watch for breakout above price
        r'(?:⚠️|🔔|❗)?\s*(?:Watch|Alert) for (?P<agg>Aggressive|Conservative)?\s*(?:breakout|break out|breaking out)\s+(?:above|over|past)\s+(?P<price>\d+(?:\.\d+)?)'
    ]
    
    # Pattern for breakdown signals
    breakdown_patterns = [
        # Standard format: Aggressive/Conservative Breakdown Below price (targets)
        r'(?:🔽|⬇️|📉|🔻)?\s*(?P<agg>Aggressive|Conservative)?\s*(?:Breakdown|Break down|Breaking down|Short)\s+(?:Below|Under|Beneath)\s+(?P<price>\d+(?:\.\d+)?)\s*(?:\((?P<targets>[^)]+)\))?',
        # Warning format: Watch for breakdown below price
        r'(?:⚠️|🔔|❗)?\s*(?:Watch|Alert) for (?P<agg>Aggressive|Conservative)?\s*(?:breakdown|break down|breaking down)\s+(?:below|under|beneath)\s+(?P<price>\d+(?:\.\d+)?)'
    ]
    
    # Pattern for rejection signals
    rejection_patterns = [
        # Standard format: Rejection Near price (targets)
        r'(?:❌|🚫|🛑|⛔)?\s*(?P<agg>Aggressive|Conservative)?\s*(?:Rejection|Reject|Rejecting)\s+(?:Near|At|Around)\s+(?P<price>\d+(?:\.\d+)?)\s*(?:\((?P<targets>[^)]+)\))?'
    ]
    
    # Pattern for bounce signals
    bounce_patterns = [
        # Standard format: Bounce From price (targets)
        r'(?:🔄|↩️|↪️|🔙)?\s*(?P<agg>Aggressive|Conservative)?\s*(?:Bounce|Bouncing|Support)\s+(?:From|Off|At)\s+(?P<price>\d+(?:\.\d+)?)\s*(?:\((?P<targets>[^)]+)\))?'
    ]
    
    # Process each line for signals
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for breakout signals
        for pattern in breakout_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group('price'))
                    aggressiveness = match.group('agg').lower() if match.group('agg') else "normal"
                    targets_str = match.group('targets') if match.groupdict().get('targets') else ""
                    targets = extract_numbers(targets_str) if targets_str else []
                    
                    signal = Signal(
                        type=SetupType.BREAKOUT.value,
                        direction=Direction.UP.value,
                        aggressiveness=aggressiveness,
                        trigger=price,
                        targets=targets
                    )
                    signals.append(signal)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error extracting breakout signal: {e}")
        
        # Check for breakdown signals
        for pattern in breakdown_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group('price'))
                    aggressiveness = match.group('agg').lower() if match.group('agg') else "normal"
                    targets_str = match.group('targets') if match.groupdict().get('targets') else ""
                    targets = extract_numbers(targets_str) if targets_str else []
                    
                    signal = Signal(
                        type=SetupType.BREAKDOWN.value,
                        direction=Direction.DOWN.value,
                        aggressiveness=aggressiveness,
                        trigger=price,
                        targets=targets
                    )
                    signals.append(signal)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error extracting breakdown signal: {e}")
        
        # Check for rejection signals
        for pattern in rejection_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group('price'))
                    aggressiveness = match.group('agg').lower() if match.group('agg') else "normal"
                    targets_str = match.group('targets') if match.groupdict().get('targets') else ""
                    targets = extract_numbers(targets_str) if targets_str else []
                    
                    # Determine direction based on context
                    direction = Direction.DOWN.value
                    if any(word in line.lower() for word in ["support", "bullish", "long"]):
                        direction = Direction.UP.value
                    
                    signal = Signal(
                        type=SetupType.REJECTION.value,
                        direction=direction,
                        aggressiveness=aggressiveness,
                        trigger=price,
                        targets=targets
                    )
                    signals.append(signal)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error extracting rejection signal: {e}")
        
        # Check for bounce signals
        for pattern in bounce_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group('price'))
                    aggressiveness = match.group('agg').lower() if match.group('agg') else "normal"
                    targets_str = match.group('targets') if match.groupdict().get('targets') else ""
                    targets = extract_numbers(targets_str) if targets_str else []
                    
                    signal = Signal(
                        type=SetupType.BOUNCE.value,
                        direction=Direction.UP.value,
                        aggressiveness=aggressiveness,
                        trigger=price,
                        targets=targets
                    )
                    signals.append(signal)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error extracting bounce signal: {e}")
    
    return signals

def extract_bias_from_text(text: str, ticker: str) -> Optional[Bias]:
    """
    Extract market bias information from text.
    
    Args:
        text: Raw text
        ticker: Ticker symbol
        
    Returns:
        Bias object if found, None otherwise
    """
    # Pattern for bias statements
    bias_patterns = [
        # Pattern for bullish/bearish bias while holding level
        r'(?:⚠️|🔔|📢|🚨)?\s*(?P<ticker>[A-Z]{1,5})?\s*(?P<bias>bulls|bears|bullish|bearish)(?:\s+in\s+charge|\s+bias|\s+sentiment)?\s+(?:while|if|when)?\s+(?:holding|above|below)\s+(?P<level>\d+(?:\.\d+)?)',
        # Pattern for breakdown only under level
        r'(?:⚠️|🔔|📢|🚨)?\s*(?:breakdown|break down|bearish)\s+(?:only|opens|active|valid)\s+(?:below|under|beneath)\s+(?P<breakdown>\d+(?:\.\d+)?)',
        # Pattern for simple bullish/bearish above/below level
        r'(?P<bias>bullish|bearish)\s+(?:above|below)\s+(?P<level>\d+(?:\.\d+)?)'
    ]
    
    for pattern in bias_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Extract the bias direction
                bias_text = match.group('bias').lower() if 'bias' in match.groupdict() and match.group('bias') else ""
                if bias_text in ["bulls", "bullish"]:
                    direction = BiasDirection.BULLISH.value
                elif bias_text in ["bears", "bearish"]:
                    direction = BiasDirection.BEARISH.value
                else:
                    continue
                
                # Extract the hold level
                if 'level' in match.groupdict() and match.group('level'):
                    hold_level = float(match.group('level'))
                else:
                    # Look for a number in the context
                    number_match = re.search(r'\d+(?:\.\d+)?', match.group(0))
                    if number_match:
                        hold_level = float(number_match.group(0))
                    else:
                        continue
                
                # Extract breakdown level if present
                breakdown_below = None
                if 'breakdown' in match.groupdict() and match.group('breakdown'):
                    breakdown_below = float(match.group('breakdown'))
                else:
                    # Look for breakdown in the text
                    breakdown_match = re.search(r'breakdown\s+(?:only|opens|active|valid)?\s+(?:below|under|beneath)\s+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
                    if breakdown_match:
                        breakdown_below = float(breakdown_match.group(1))
                
                return Bias(
                    direction=direction,
                    hold_level=hold_level,
                    breakdown_below=breakdown_below
                )
            
            except (ValueError, AttributeError) as e:
                logger.debug(f"Error extracting bias: {e}")
    
    return None

def extract_numbers(text: str) -> List[float]:
    """
    Extract numbers from text.
    
    Args:
        text: Text containing numbers
        
    Returns:
        List of extracted numbers as floats
    """
    number_pattern = r'\d+(?:\.\d+)?'
    matches = re.findall(number_pattern, text)
    
    return [float(match) for match in matches]

def extract_unique_levels(signals: List[Signal]) -> Set[float]:
    """
    Extract and deduplicate price levels from signals.
    
    Args:
        signals: List of Signal objects
        
    Returns:
        Set of unique price levels
    """
    unique_levels = set()
    
    for signal in signals:
        # Add trigger price
        unique_levels.add(signal.trigger)
        
        # Add target prices
        for target in signal.targets:
            unique_levels.add(target)
    
    return unique_levels

# Common emoji set for recognition
emoji_set = {
    "🔼", "⬆️", "🚀", "🔝", "🔽", "⬇️", "📉", "🔻", 
    "❌", "🚫", "🛑", "⛔", "🔄", "↩️", "↪️", "🔙",
    "⚠️", "🔔", "📢", "🚨", "❗", "‼️", "⁉️"
}