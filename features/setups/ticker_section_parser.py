"""
Ticker Section Parser

This module implements the section-based approach for parsing multi-ticker messages,
following the suggestions in the attached file.
"""
import re
import logging
from typing import List, Dict, Any, Optional

from common.models import (
    TradeSetupMessage,
    TickerSetup,
    Signal,
    Bias,
    SignalCategory,
    ComparisonType,
    Aggressiveness,
    BiasDirection
)

logger = logging.getLogger(__name__)

def normalize_emojis(text: str) -> str:
    """
    Replace emojis with text markers for easier pattern matching.
    """
    return text.replace("🔼", "[BREAKOUT]")\
               .replace("⬆️", "[BREAKOUT]")\
               .replace("🔻", "[BREAKDOWN]")\
               .replace("⬇️", "[BREAKDOWN]")\
               .replace("❌", "[REJECTION]")\
               .replace("🔄", "[BOUNCE]")\
               .replace("⚠️", "[WARNING]")

def split_message_into_sections(text: str) -> List[Dict[str, str]]:
    """
    Split a trading message into ticker-specific sections.
    
    Args:
        text: The raw message text
        
    Returns:
        List of dictionaries with 'symbol' and 'body' for each ticker section
    """
    normalized_text = normalize_emojis(text)
    
    # Try different section patterns, from most to least structured
    section_patterns = [
        # Pattern 1: Numbered with parenthesis - "1) SPY: Signal..."
        re.compile(
            r'(?ms)^\s*\d+\)\s+([A-Z]{1,5}):\s*(.*?)(?=^\s*\d+\)\s+[A-Z]{1,5}:|\Z)',
            re.MULTILINE
        ),
        # Pattern 2: Numbered with period - "1. SPY: Signal..."
        re.compile(
            r'(?ms)^\s*\d+\.\s+([A-Z]{1,5}):\s*(.*?)(?=^\s*\d+\.\s+[A-Z]{1,5}:|\Z)',
            re.MULTILINE
        ),
        # Pattern 3: Just the ticker name on its own line - "SPY\nSignal..."
        re.compile(
            r'(?ms)^([A-Z]{1,5})$\s*(.*?)(?=^[A-Z]{1,5}$|\Z)',
            re.MULTILINE
        )
    ]
    
    # Try each pattern until we find sections
    for pattern in section_patterns:
        matches = list(pattern.finditer(normalized_text))
        if matches:
            sections = []
            for match in matches:
                symbol = match.group(1)
                body = match.group(2)
                sections.append({
                    'symbol': symbol,
                    'body': body
                })
            logger.debug(f"Found {len(sections)} ticker sections using pattern: {pattern.pattern}")
            return sections
    
    # Handle special cases with inline ticker mentions
    if re.search(r'[A-Z]{1,5}:', normalized_text):
        inline_pattern = re.compile(r'([A-Z]{1,5}):(.*?)(?=[A-Z]{1,5}:|\Z)', re.DOTALL)
        matches = list(inline_pattern.finditer(normalized_text))
        if matches:
            sections = []
            for match in matches:
                symbol = match.group(1)
                body = match.group(2)
                sections.append({
                    'symbol': symbol,
                    'body': body
                })
            logger.debug(f"Found {len(sections)} ticker sections using inline pattern")
            return sections
    
    return []

def extract_signal_from_section(section: Dict[str, str]) -> List[Signal]:
    """
    Extract signals from a ticker section using a small dictionary of patterns.
    
    Args:
        section: Dictionary with 'symbol' and 'body' keys
        
    Returns:
        List of Signal objects
    """
    symbol = section['symbol']
    body = section['body']
    
    # Define signal patterns with named groups
    signal_patterns = {
        'breakout': re.compile(r'(?:\[BREAKOUT\]|Breakout|Long)\s+(?:Above|Over)\s+(\d+\.\d+)', re.IGNORECASE),
        'breakdown': re.compile(r'(?:\[BREAKDOWN\]|Breakdown|Short)\s+(?:Below|Under)\s+(\d+\.\d+)', re.IGNORECASE),
        'rejection': re.compile(r'(?:\[REJECTION\]|Rejection)\s+(?:Near|At|Around)\s+(\d+\.\d+)', re.IGNORECASE),
        'bounce': re.compile(r'(?:\[BOUNCE\]|Bounce)\s+(?:From|Near|At)\s+(\d+\.\d+)', re.IGNORECASE)
    }
    
    signals = []
    
    # Apply each pattern and create signals
    for signal_type, pattern in signal_patterns.items():
        for match in pattern.finditer(body):
            price = float(match.group(1))
            
            if signal_type == 'breakout':
                signals.append(Signal(
                    category=SignalCategory.BREAKOUT,
                    aggressiveness=Aggressiveness.NONE,
                    comparison=ComparisonType.ABOVE,
                    trigger=price,
                    targets=[price]  # Will be updated with targets later
                ))
            elif signal_type == 'breakdown':
                signals.append(Signal(
                    category=SignalCategory.BREAKDOWN,
                    aggressiveness=Aggressiveness.NONE,
                    comparison=ComparisonType.BELOW,
                    trigger=price,
                    targets=[price]  # Will be updated with targets later
                ))
            elif signal_type == 'rejection':
                signals.append(Signal(
                    category=SignalCategory.REJECTION,
                    aggressiveness=Aggressiveness.NONE,
                    comparison=ComparisonType.NEAR,
                    trigger=price,
                    targets=[price]  # Will be updated with targets later
                ))
            elif signal_type == 'bounce':
                signals.append(Signal(
                    category=SignalCategory.BOUNCE,
                    aggressiveness=Aggressiveness.NONE,
                    comparison=ComparisonType.NEAR,
                    trigger=price,
                    targets=[price]  # Will be updated with targets later
                ))
    
    # If we found signals, extract targets
    if signals:
        targets = []
        
        # Look for format "Target 1: 185, Target 2: 190"
        target_matches = re.finditer(r'Target\s+\d+:\s+(\d+\.\d+)', body)
        for match in target_matches:
            targets.append(float(match.group(1)))
        
        # Look for format "Target: 495"
        if not targets:
            target_match = re.search(r'Target:\s+(\d+\.\d+)', body)
            if target_match:
                targets.append(float(target_match.group(1)))
        
        # Apply targets to all signals
        if targets:
            for signal in signals:
                signal.targets = targets
    
    return signals

def extract_bias_from_section(section: Dict[str, str]) -> Optional[Bias]:
    """
    Extract bias information from a ticker section.
    
    Args:
        section: Dictionary with 'symbol' and 'body' keys
        
    Returns:
        Bias object if found, None otherwise
    """
    body = section['body'].lower()
    
    # Check for standard bias format
    bullish_match = re.search(r'bullish\s+bias\s+above\s+(\d+\.\d+)', body)
    if bullish_match:
        price = float(bullish_match.group(1))
        return Bias(
            direction=BiasDirection.BULLISH,
            condition=ComparisonType.ABOVE,
            price=price,
            flip=None
        )
    
    bearish_match = re.search(r'bearish\s+bias\s+below\s+(\d+\.\d+)', body)
    if bearish_match:
        price = float(bearish_match.group(1))
        return Bias(
            direction=BiasDirection.BEARISH,
            condition=ComparisonType.BELOW,
            price=price,
            flip=None
        )
    
    # Check for warning format
    if "[warning]" in body:
        if "bullish" in body and "above" in body:
            price_match = re.search(r'above\s+(\d+\.\d+)', body)
            if price_match:
                price = float(price_match.group(1))
                return Bias(
                    direction=BiasDirection.BULLISH,
                    condition=ComparisonType.ABOVE,
                    price=price,
                    flip=None
                )
        
        if "bearish" in body and "below" in body:
            price_match = re.search(r'below\s+(\d+\.\d+)', body)
            if price_match:
                price = float(price_match.group(1))
                return Bias(
                    direction=BiasDirection.BEARISH,
                    condition=ComparisonType.BELOW,
                    price=price,
                    flip=None
                )
    
    return None

def parse_sections(sections: List[Dict[str, str]]) -> List[TickerSetup]:
    """
    Parse ticker sections into TickerSetup objects.
    
    Args:
        sections: List of dictionaries with 'symbol' and 'body' keys
        
    Returns:
        List of TickerSetup objects
    """
    ticker_setups = []
    
    for section in sections:
        symbol = section['symbol']
        
        # Extract signals
        signals = extract_signal_from_section(section)
        
        # Extract bias
        bias = extract_bias_from_section(section)
        
        # Add ticker setup if we found signals
        if signals:
            ticker_setups.append(TickerSetup(
                symbol=symbol,
                signals=signals,
                bias=bias,
                text=f"{symbol}: {section['body']}"
            ))
    
    return ticker_setups