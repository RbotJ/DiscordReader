"""
Multi-Ticker Parser Module

This module implements the section-based approach for parsing trade setup messages
with multiple ticker symbols, following the suggestions for improved reliability.
"""
import re
import logging
from typing import List, Dict, Optional, Any

from common.models import (
    Signal,
    Bias,
    TickerSetup,
    SignalCategory,
    ComparisonType,
    Aggressiveness,
    BiasDirection
)

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Replace emojis with text markers for easier parsing."""
    return text.replace("🔼", "[BREAKOUT]")\
              .replace("⬆️", "[BREAKOUT]")\
              .replace("🔻", "[BREAKDOWN]")\
              .replace("⬇️", "[BREAKDOWN]")\
              .replace("❌", "[REJECTION]")\
              .replace("🔄", "[BOUNCE]")\
              .replace("⚠️", "[WARNING]")

def extract_ticker_sections(text: str) -> List[Dict[str, str]]:
    """
    Split a message into separate sections by ticker using regex patterns.
    
    Args:
        text: The normalized message text
        
    Returns:
        List of dicts with 'symbol' and 'text' keys for each ticker section
    """
    section_patterns = [
        # Pattern 1: Numbered with parenthesis: "1) SPY: ..."
        re.compile(r'(?ms)^\s*\d+\)\s+([A-Z]{1,5}):\s*(.*?)(?=^\s*\d+\)\s+[A-Z]{1,5}:|\Z)', re.MULTILINE),
        
        # Pattern 2: Numbered with period: "1. SPY: ..."
        re.compile(r'(?ms)^\s*\d+\.\s+([A-Z]{1,5}):\s*(.*?)(?=^\s*\d+\.\s+[A-Z]{1,5}:|\Z)', re.MULTILINE),
        
        # Pattern 3: Just ticker name on line: "SPY\n..."
        re.compile(r'(?ms)^([A-Z]{1,5})$\s*(.*?)(?=^[A-Z]{1,5}$|\Z)', re.MULTILINE),
        
        # Pattern 4: Ticker with colon at beginning of line: "SPY: Breakout..."
        re.compile(r'(?ms)^([A-Z]{1,5}):\s*(.*?)(?=^[A-Z]{1,5}:|\Z)', re.MULTILINE),
    ]
    
    # Try each pattern until we find sections
    for pattern in section_patterns:
        matches = list(pattern.finditer(text))
        if matches:
            sections = []
            for match in matches:
                symbol = match.group(1)
                section_text = match.group(2)
                sections.append({
                    'symbol': symbol,
                    'text': section_text
                })
            logger.debug(f"Found {len(sections)} ticker sections using pattern: {pattern.pattern}")
            return sections
    
    # No sections found with the patterns
    return []

def extract_signal_from_section(section: Dict[str, str]) -> List[Signal]:
    """
    Extract signals from a ticker section.
    
    Args:
        section: Dictionary with 'symbol' and 'text' keys
        
    Returns:
        List of Signal objects
    """
    symbol = section['symbol']
    text = section['text']
    full_text = f"{symbol}: {text}"  # Add symbol prefix for header patterns
    signals = []
    
    # Check header for common formats
    header_pattern = re.compile(rf"(?:{symbol}):\s*(Breakout|Breakdown|Rejection|Bounce)\s+(Above|Below|Near|Over|Under)\s+(\d+\.\d+)", re.IGNORECASE)
    header_match = header_pattern.search(full_text)
    
    # Alternative header pattern for formats like "SPY: Breakout Above 587" within section text
    if not header_match and ":" in text:
        alt_header_pattern = re.compile(r".*?(Breakout|Breakdown|Rejection|Bounce)\s+(Above|Below|Near|Over|Under)\s+(\d+\.\d+)", re.IGNORECASE)
        header_match = alt_header_pattern.search(text)
    
    if header_match:
        signal_type = header_match.group(1).lower()
        comparison = header_match.group(2).lower()
        price = float(header_match.group(3))
        
        # Create signal based on header
        if 'breakout' in signal_type:
            signals.append(Signal(
                category=SignalCategory.BREAKOUT,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.ABOVE,
                trigger=price,
                targets=[price]  # Default target, will look for explicit targets below
            ))
        elif 'breakdown' in signal_type:
            signals.append(Signal(
                category=SignalCategory.BREAKDOWN,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.BELOW,
                trigger=price,
                targets=[price]  # Default target, will look for explicit targets below
            ))
        elif 'rejection' in signal_type:
            signals.append(Signal(
                category=SignalCategory.REJECTION,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.NEAR,
                trigger=price,
                targets=[price]  # Default target, will look for explicit targets below
            ))
        elif 'bounce' in signal_type:
            signals.append(Signal(
                category=SignalCategory.BOUNCE,
                aggressiveness=Aggressiveness.NONE,
                comparison=ComparisonType.NEAR,
                trigger=price,
                targets=[price]  # Default target, will look for explicit targets below
            ))
    
    # If header pattern didn't match, try inline patterns
    if not signals:
        # Patterns for different signal types
        signal_patterns = {
            'breakout': re.compile(r'(?:Breakout|\[BREAKOUT\])\s+(?:Above|Over)\s+(\d+\.\d+)', re.IGNORECASE),
            'breakdown': re.compile(r'(?:Breakdown|\[BREAKDOWN\])\s+(?:Below|Under)\s+(\d+\.\d+)', re.IGNORECASE),
            'rejection': re.compile(r'(?:Rejection|\[REJECTION\])\s+(?:Near|At)\s+(\d+\.\d+)', re.IGNORECASE),
            'bounce': re.compile(r'(?:Bounce|\[BOUNCE\])\s+(?:From|Near)\s+(\d+\.\d+)', re.IGNORECASE)
        }
        
        # Try each pattern to find signals
        for signal_type, pattern in signal_patterns.items():
            for match in pattern.finditer(text):
                price = float(match.group(1))
                
                # Create the appropriate signal based on type
                signal = None
                if signal_type == 'breakout':
                    signal = Signal(
                        category=SignalCategory.BREAKOUT,
                        aggressiveness=Aggressiveness.NONE,
                        comparison=ComparisonType.ABOVE,
                        trigger=price,
                        targets=[price]  # Default target, will look for explicit targets below
                    )
                elif signal_type == 'breakdown':
                    signal = Signal(
                        category=SignalCategory.BREAKDOWN,
                        aggressiveness=Aggressiveness.NONE,
                        comparison=ComparisonType.BELOW,
                        trigger=price,
                        targets=[price]  # Default target, will look for explicit targets below
                    )
                elif signal_type == 'rejection':
                    signal = Signal(
                        category=SignalCategory.REJECTION,
                        aggressiveness=Aggressiveness.NONE,
                        comparison=ComparisonType.NEAR,
                        trigger=price,
                        targets=[price]  # Default target, will look for explicit targets below
                    )
                elif signal_type == 'bounce':
                    signal = Signal(
                        category=SignalCategory.BOUNCE,
                        aggressiveness=Aggressiveness.NONE,
                        comparison=ComparisonType.NEAR,
                        trigger=price,
                        targets=[price]  # Default target, will look for explicit targets below
                    )
                
                if signal:
                    signals.append(signal)
    
    # If we found any signals, extract targets
    if signals:
        # Extract targets using "Target X: Y.YY" format
        targets = []
        target_matches = re.finditer(r'Target\s+\d+:\s+(\d+\.\d+)', text)
        for match in target_matches:
            targets.append(float(match.group(1)))
        
        # Also check for simple "Target: X.XX" format
        if not targets:
            simple_target = re.search(r'Target:\s+(\d+\.\d+)', text)
            if simple_target:
                targets.append(float(simple_target.group(1)))
        
        # Apply targets to all signals if found
        if targets:
            for signal in signals:
                signal.targets = targets
    
    return signals

def extract_bias_from_section(section: Dict[str, str]) -> Optional[Bias]:
    """
    Extract bias information from a ticker section.
    
    Args:
        section: Dictionary with 'symbol' and 'text' keys
        
    Returns:
        Bias object if found, None otherwise
    """
    text = section['text'].lower()
    
    # Pattern 1: Explicit bias statements with "bias" keyword
    bullish_match = re.search(r'bullish\s+bias\s+above\s+(\d+\.\d+)', text)
    if bullish_match:
        price = float(bullish_match.group(1))
        return Bias(
            direction=BiasDirection.BULLISH,
            condition=ComparisonType.ABOVE,
            price=price,
            flip=None
        )
    
    bearish_match = re.search(r'bearish\s+bias\s+below\s+(\d+\.\d+)', text)
    if bearish_match:
        price = float(bearish_match.group(1))
        return Bias(
            direction=BiasDirection.BEARISH,
            condition=ComparisonType.BELOW,
            price=price,
            flip=None
        )
    
    # Pattern 2: Simple "Bullish above X.XX" format
    simple_bullish = re.search(r'bullish\s+above\s+(\d+\.\d+)', text)
    if simple_bullish:
        price = float(simple_bullish.group(1))
        return Bias(
            direction=BiasDirection.BULLISH,
            condition=ComparisonType.ABOVE,
            price=price,
            flip=None
        )
    
    # Pattern 3: Simple "Bearish below X.XX" format
    simple_bearish = re.search(r'bearish\s+below\s+(\d+\.\d+)', text)
    if simple_bearish:
        price = float(simple_bearish.group(1))
        return Bias(
            direction=BiasDirection.BEARISH,
            condition=ComparisonType.BELOW,
            price=price,
            flip=None
        )
    
    # Pattern 4: Look for bias near warning symbol
    if "[warning]" in text:
        if "bullish" in text and "above" in text:
            price_match = re.search(r'above\s+(\d+\.\d+)', text)
            if price_match:
                price = float(price_match.group(1))
                return Bias(
                    direction=BiasDirection.BULLISH,
                    condition=ComparisonType.ABOVE,
                    price=price,
                    flip=None
                )
        elif "bearish" in text and "below" in text:
            price_match = re.search(r'below\s+(\d+\.\d+)', text)
            if price_match:
                price = float(price_match.group(1))
                return Bias(
                    direction=BiasDirection.BEARISH,
                    condition=ComparisonType.BELOW,
                    price=price,
                    flip=None
                )
    
    # Pattern 5: Infer bias from signal type - a SPY breakout above is bullish
    breakout_match = re.search(r'breakout\s+above\s+(\d+\.\d+)', text)
    if breakout_match:
        price = float(breakout_match.group(1))
        return Bias(
            direction=BiasDirection.BULLISH,
            condition=ComparisonType.ABOVE,
            price=price,
            flip=None
        )
    
    # Pattern 6: Infer bias from signal type - a SPY breakdown below is bearish
    breakdown_match = re.search(r'breakdown\s+below\s+(\d+\.\d+)', text)
    if breakdown_match:
        price = float(breakdown_match.group(1))
        return Bias(
            direction=BiasDirection.BEARISH,
            condition=ComparisonType.BELOW,
            price=price,
            flip=None
        )
    
    return None

def process_ticker_sections(sections: List[Dict[str, str]]) -> List[TickerSetup]:
    """
    Process each ticker section to extract signals and bias.
    
    Args:
        sections: List of dictionaries with 'symbol' and 'text' keys
        
    Returns:
        List of TickerSetup objects
    """
    ticker_setups = []
    
    for section in sections:
        symbol = section['symbol']
        section_text = section['text']
        
        # Extract signals
        signals = extract_signal_from_section(section)
        
        # Extract bias
        bias = extract_bias_from_section(section)
        
        # Only add a ticker setup if we found signals
        if signals:
            ticker_setups.append(TickerSetup(
                symbol=symbol,
                signals=signals,
                bias=bias,
                text=f"{symbol}: {section_text}"
            ))
            logger.debug(f"Created setup for {symbol} with {len(signals)} signals and bias={bias is not None}")
    
    return ticker_setups