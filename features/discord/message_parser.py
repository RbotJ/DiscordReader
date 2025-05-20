"""
Discord Message Parser

This module handles parsing Discord messages for trading setups and signals.
It extracts ticker symbols, signal types, price targets, and other relevant information.
"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

# Regular expressions for parsing
TICKER_PATTERN = r'\$?([A-Z]{1,5})'
PRICE_PATTERN = r'(?:\$|price:?\s*)(\d+\.?\d*)'
RESISTANCE_PATTERN = r'(?:resistance|res)(?:\s+at)?\s*:?\s*(\d+\.?\d*)'
SUPPORT_PATTERN = r'(?:support|sup)(?:\s+at)?\s*:?\s*(\d+\.?\d*)'
TARGET_PATTERN = r'(?:target|tgt)(?:\s+at)?\s*:?\s*(\d+\.?\d*)'
STOP_PATTERN = r'(?:stop|sl)(?:\s+at)?\s*:?\s*(\d+\.?\d*)'
ENTRY_PATTERN = r'(?:entry|enter)(?:\s+at)?\s*:?\s*(\d+\.?\d*)'
EXPIRY_PATTERN = r'(?:expiry|exp)(?:\s+at)?\s*:?\s*(\d+[dw])'

# Signal types
SIGNAL_TYPES = {
    'breakout': ['breakout', 'break out', 'breaking out', 'breaks out'],
    'breakdown': ['breakdown', 'break down', 'breaking down', 'breaks down'],
    'rejection': ['rejection', 'reject', 'rejecting', 'rejects'],
    'bounce': ['bounce', 'bouncing', 'bounces', 'bounced'],
    'support': ['support', 'holding support'],
    'resistance': ['resistance', 'at resistance'],
    'bullish': ['bullish', 'bull', 'long', 'calls', 'call option', 'calls looking good'],
    'bearish': ['bearish', 'bear', 'short', 'puts', 'put option', 'puts looking good']
}

def parse_message(message: str) -> Dict:
    """
    Parse a Discord message for trading setup information.
    
    Args:
        message: Raw message text
        
    Returns:
        Dictionary containing extracted information
    """
    try:
        # Clean up the message
        cleaned_message = message.replace('\n', ' ').strip()
        
        # Extract basic information
        tickers = extract_tickers(cleaned_message)
        prices = extract_prices(cleaned_message)
        signal_type = detect_signal_type(cleaned_message)
        bias = detect_bias(cleaned_message)
        
        # Extract levels
        support_levels = extract_support_levels(cleaned_message)
        resistance_levels = extract_resistance_levels(cleaned_message)
        target_levels = extract_target_levels(cleaned_message)
        stop_levels = extract_stop_levels(cleaned_message)
        entry_levels = extract_entry_levels(cleaned_message)
        
        # Build the result
        result = {
            'datetime': datetime.now().isoformat(),
            'raw_message': message,
            'tickers': list(tickers),
            'signal_type': signal_type,
            'bias': bias,
            'detected_prices': prices,
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'target_levels': target_levels,
            'stop_levels': stop_levels,
            'entry_levels': entry_levels
        }
        
        # Determine primary ticker (if multiple found)
        if tickers:
            primary_ticker = determine_primary_ticker(cleaned_message, tickers)
            result['primary_ticker'] = primary_ticker
        
        # Add confidence level based on completeness of the setup
        confidence = calculate_confidence(result)
        result['confidence'] = confidence
        
        logger.info(f"Successfully parsed message: {result['tickers']} - {result['signal_type']}")
        return result
        
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        return {
            'datetime': datetime.now().isoformat(),
            'raw_message': message,
            'error': str(e),
            'tickers': [],
            'signal_type': None,
            'bias': None
        }

def extract_tickers(text: str) -> Set[str]:
    """
    Extract ticker symbols from text.
    
    Args:
        text: Text to extract tickers from
        
    Returns:
        Set of ticker symbols
    """
    matches = re.findall(TICKER_PATTERN, text)
    
    # Filter out common words that match the pattern but aren't tickers
    non_tickers = {'A', 'I', 'AT', 'BE', 'BY', 'DO', 'GO', 'IF', 'IN', 'IS', 'IT', 'ME', 'MY', 'ON', 'OR', 'SO', 'TO', 'UP', 'US', 'WE'}
    
    return {match for match in matches if match not in non_tickers and len(match) >= 1 and len(match) <= 5}

def detect_signal_type(text: str) -> Optional[str]:
    """
    Detect signal type from text.
    
    Args:
        text: Text to detect signal type from
        
    Returns:
        Signal type or None if not detected
    """
    text_lower = text.lower()
    
    for signal_type, keywords in SIGNAL_TYPES.items():
        for keyword in keywords:
            if keyword in text_lower:
                return signal_type
                
    return None

def detect_bias(text: str) -> Optional[str]:
    """
    Detect trading bias (bullish/bearish) from text.
    
    Args:
        text: Text to detect bias from
        
    Returns:
        'bullish', 'bearish', or None if not detected
    """
    text_lower = text.lower()
    
    bullish_terms = SIGNAL_TYPES['bullish']
    bearish_terms = SIGNAL_TYPES['bearish']
    
    for term in bullish_terms:
        if term in text_lower:
            return 'bullish'
            
    for term in bearish_terms:
        if term in text_lower:
            return 'bearish'
            
    # Infer from signal type
    if 'breakout' in text_lower or 'bounce' in text_lower:
        return 'bullish'
    elif 'breakdown' in text_lower or 'rejection' in text_lower:
        return 'bearish'
        
    return None

def extract_prices(text: str) -> List[float]:
    """
    Extract price values from text.
    
    Args:
        text: Text to extract prices from
        
    Returns:
        List of prices
    """
    matches = re.findall(PRICE_PATTERN, text)
    return [float(match) for match in matches]

def extract_support_levels(text: str) -> List[float]:
    """
    Extract support levels from text.
    
    Args:
        text: Text to extract support levels from
        
    Returns:
        List of support levels
    """
    matches = re.findall(SUPPORT_PATTERN, text)
    return [float(match) for match in matches]

def extract_resistance_levels(text: str) -> List[float]:
    """
    Extract resistance levels from text.
    
    Args:
        text: Text to extract resistance levels from
        
    Returns:
        List of resistance levels
    """
    matches = re.findall(RESISTANCE_PATTERN, text)
    return [float(match) for match in matches]

def extract_target_levels(text: str) -> List[float]:
    """
    Extract target levels from text.
    
    Args:
        text: Text to extract target levels from
        
    Returns:
        List of target levels
    """
    matches = re.findall(TARGET_PATTERN, text)
    return [float(match) for match in matches]

def extract_stop_levels(text: str) -> List[float]:
    """
    Extract stop loss levels from text.
    
    Args:
        text: Text to extract stop loss levels from
        
    Returns:
        List of stop loss levels
    """
    matches = re.findall(STOP_PATTERN, text)
    return [float(match) for match in matches]

def extract_entry_levels(text: str) -> List[float]:
    """
    Extract entry levels from text.
    
    Args:
        text: Text to extract entry levels from
        
    Returns:
        List of entry levels
    """
    matches = re.findall(ENTRY_PATTERN, text)
    return [float(match) for match in matches]

def determine_primary_ticker(text: str, tickers: Set[str]) -> str:
    """
    Determine the primary ticker from a set of extracted tickers.
    
    Args:
        text: Original message text
        tickers: Set of extracted tickers
        
    Returns:
        Primary ticker symbol
    """
    if len(tickers) == 1:
        return list(tickers)[0]
        
    # Count occurrences
    ticker_counts = {}
    for ticker in tickers:
        # Look for exact matches with $ or word boundaries
        pattern = r'(?:\$|^|\s)' + ticker + r'(?:$|\s|\.|,|:|;)'
        matches = re.findall(pattern, text)
        ticker_counts[ticker] = len(matches)
    
    # Find the most frequent ticker
    if ticker_counts:
        primary_ticker = max(ticker_counts.items(), key=lambda x: x[1])
        return primary_ticker[0]
    
    # Fallback: return the first ticker in the original order
    return list(tickers)[0]

def calculate_confidence(setup_data: Dict) -> float:
    """
    Calculate confidence level of a trade setup based on completeness.
    
    Args:
        setup_data: Dictionary containing extracted setup data
        
    Returns:
        Confidence level (0.0-1.0)
    """
    # Start with base confidence
    confidence = 0.5
    
    # Add confidence based on available data
    if setup_data.get('tickers'):
        confidence += 0.1
    if setup_data.get('signal_type'):
        confidence += 0.1
    if setup_data.get('bias'):
        confidence += 0.05
    if setup_data.get('support_levels') or setup_data.get('resistance_levels'):
        confidence += 0.1
    if setup_data.get('target_levels'):
        confidence += 0.1
    if setup_data.get('stop_levels'):
        confidence += 0.05
    
    # Cap at 1.0
    return min(confidence, 1.0)

def validate_setup(setup_data: Dict) -> bool:
    """
    Validate if a setup has the minimum required information.
    
    Args:
        setup_data: Dictionary containing extracted setup data
        
    Returns:
        True if valid, False otherwise
    """
    # Minimum requirements: ticker, signal type or bias, and at least one price level
    has_ticker = bool(setup_data.get('tickers'))
    has_signal = bool(setup_data.get('signal_type') or setup_data.get('bias'))
    has_price_level = bool(
        setup_data.get('detected_prices') or
        setup_data.get('support_levels') or
        setup_data.get('resistance_levels') or
        setup_data.get('target_levels') or
        setup_data.get('entry_levels')
    )
    
    return has_ticker and has_signal and has_price_level