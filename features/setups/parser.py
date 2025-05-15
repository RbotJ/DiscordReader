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
DATE_PATTERN = r"A\+ Trade Setups[^\n]*(?:[—–]|\s+)(\w{3}\s+\w{3}\s+\d{1,2})"
TICKER_PATTERN = r"(?:\d+\)\s+|—{2,}[\r\n]+)([A-Z]+)"
BREAKOUT_PATTERN = r"🔼\s+(?:Breakout|Breakout Entry|Breakout Entries)\s+(?:(Aggressive|Conservative))?\s*(?:Above|Over)\s+(\d+\.\d+)"
BREAKDOWN_PATTERN = r"🔻\s+(?:Breakdown|Breakdown Entry|Breakdown Entries)\s+(?:(Aggressive|Conservative))?\s*(?:Below|Under)\s+(\d+\.\d+)"
REJECTION_PATTERN = r"❌\s+(?:Rejection|Rejection Short|Rejection Short Zone|Rejection Short Zones|Rejection Levels)(?:\s+Near)?\s+(\d+\.\d+)"
BOUNCE_PATTERN = r"🔄\s+(?:Bounce|Bounce From|Bounce Entry|Bounce Long Zones|Bounce Zone)\s+(?:From|Near)?\s+(\d+\.\d+)"
BOUNCE_ZONE_PATTERN = r"🌀\s+(?:Bounce Zone|Bounce Long Zones)\s+(?:Near)?\s+(?:(\d+\.\d+)[-–](\d+\.\d+)|(\d+\.\d+))"
TARGET_PATTERN = r"(?:🔼|🔻)\s+(?:Targets|Target)?:?\s*(?:(\d+\.\d+)(?:,\s*|-)?)+"
BIAS_PATTERN = r"⚠️\s+(?:Bias\s+)?(Bullish|Bearish)[^0-9.,\n]*(?:above|below|under|over|while holding above|while holding below)\s+(\d+\.\d+)"
BIAS_FLIP_PATTERN = r"(?:flips|flip to) (bullish|bearish)(?:[^0-9.,\n]*)(?:on|if|when|above|below|over|under)[^0-9.,\n]*(\d+\.\d+)"

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
            aggressiveness_str = breakout_match.group(1) if breakout_match.group(1) else "none"
            aggressiveness = (Aggressiveness.AGGRESSIVE if aggressiveness_str.lower() == "aggressive" else
                             Aggressiveness.CONSERVATIVE if aggressiveness_str.lower() == "conservative" else
                             Aggressiveness.NONE)
            
            trigger_price = float(breakout_match.group(2))
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
            aggressiveness_str = breakdown_match.group(1) if breakdown_match.group(1) else "none"
            aggressiveness = (Aggressiveness.AGGRESSIVE if aggressiveness_str.lower() == "aggressive" else
                             Aggressiveness.CONSERVATIVE if aggressiveness_str.lower() == "conservative" else
                             Aggressiveness.NONE)
            
            trigger_price = float(breakdown_match.group(2))
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
    
    return signals


def extract_bias(text: str, symbol: str) -> Optional[Bias]:
    """Extract bias information for a ticker symbol."""
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
        return None
    
    if end_idx is None:
        end_idx = len(lines)
    
    ticker_text = "\n".join(lines[start_idx:end_idx])
    
    # Extract bias
    bias_match = re.search(BIAS_PATTERN, ticker_text)
    if not bias_match:
        return None
    
    direction_str = bias_match.group(1).lower()
    direction = BiasDirection.BULLISH if direction_str == "bullish" else BiasDirection.BEARISH
    price = float(bias_match.group(2))
    
    # Determine comparison type from context
    comparison = ComparisonType.ABOVE
    if "below" in bias_match.group(0).lower() or "under" in bias_match.group(0).lower():
        comparison = ComparisonType.BELOW
    
    # Check for bias flip
    flip = None
    bias_flip_match = re.search(BIAS_FLIP_PATTERN, ticker_text)
    if bias_flip_match:
        flip_direction_str = bias_flip_match.group(1).lower()
        flip_direction = BiasDirection.BULLISH if flip_direction_str == "bullish" else BiasDirection.BEARISH
        flip_price = float(bias_flip_match.group(2))
        
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


def extract_tickers(text: str) -> List[str]:
    """Extract ticker symbols from the message."""
    tickers = []
    
    # Look for numbered tickers
    numbered_tickers = re.findall(r"\d+\)\s+([A-Z]+)", text)
    if numbered_tickers:
        tickers.extend(numbered_tickers)
    
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
    
    return tickers


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
    message_date = parse_date(date_match.group(1)) if date_match else date.today()
    
    # Extract tickers
    tickers = extract_tickers(text)
    
    # Process each ticker
    ticker_setups = []
    for symbol in tickers:
        signals = extract_signals(text, symbol)
        bias = extract_bias(text, symbol)
        
        if signals:
            ticker_setups.append(TickerSetup(
                symbol=symbol,
                signals=signals,
                bias=bias
            ))
    
    # Create the complete message
    return TradeSetupMessage(
        date=message_date,
        raw_text=text,
        setups=ticker_setups,
        source=source,
        created_at=datetime.now()
    )