"""
Common Parser Utilities Module

Provides shared utility functions for parsing Discord messages and extracting 
trading setup information. These utilities are used across multiple parsing modules.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalize text for parsing by cleaning whitespace and formatting.
    
    Args:
        text: Raw text to normalize
        
    Returns:
        str: Normalized text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Normalize common trading symbols
    text = re.sub(r'🔻', 'DOWN', text)
    text = re.sub(r'🔼', 'UP', text)
    text = re.sub(r'🔄', 'BOUNCE', text)
    text = re.sub(r'❌', 'REJECT', text)
    text = re.sub(r'✅', 'CONFIRM', text)
    text = re.sub(r'⚠️', 'WARNING', text)
    
    return text


def extract_ticker_sections(text: str) -> List[Dict[str, Any]]:
    """
    Extract ticker sections from message text.
    
    Args:
        text: Message text to parse
        
    Returns:
        List[Dict]: List of ticker sections with metadata
    """
    sections = []
    
    # Common ticker patterns (SPY, NVDA, TSLA, etc.)
    ticker_pattern = r'\b([A-Z]{2,5})\b'
    
    # Split text by common separators
    parts = re.split(r'\n\n+', text)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Look for ticker at start of section
        ticker_match = re.search(ticker_pattern, part)
        if ticker_match:
            ticker = ticker_match.group(1)
            
            # Skip common words that match pattern but aren't tickers
            if ticker in ['THE', 'AND', 'FOR', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'USE', 'MAN', 'NEW', 'NOW', 'WAY', 'MAY', 'SAY']:
                continue
                
            sections.append({
                'ticker': ticker,
                'content': part,
                'raw_text': part
            })
    
    return sections


def process_ticker_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process ticker sections to extract structured data.
    
    Args:
        sections: List of ticker sections
        
    Returns:
        List[Dict]: Processed sections with extracted data
    """
    processed = []
    
    for section in sections:
        try:
            processed_section = {
                'ticker': section['ticker'],
                'content': section['content'],
                'signals': extract_signal_from_section(section['content']),
                'bias': extract_bias_from_section(section['content']),
                'targets': _extract_price_targets(section['content']),
                'levels': _extract_price_levels(section['content'])
            }
            processed.append(processed_section)
            
        except Exception as e:
            logger.warning(f"Error processing section for {section.get('ticker', 'unknown')}: {e}")
            continue
    
    return processed


def extract_signal_from_section(text: str) -> List[str]:
    """
    Extract trading signals from section text.
    
    Args:
        text: Section text to analyze
        
    Returns:
        List[str]: Extracted signals
    """
    signals = []
    text_upper = text.upper()
    
    # Signal patterns
    signal_patterns = [
        (r'BREAKOUT\s+ABOVE\s+([\d.]+)', 'BREAKOUT_ABOVE'),
        (r'BREAKDOWN\s+BELOW\s+([\d.]+)', 'BREAKDOWN_BELOW'),
        (r'REJECTION\s+(?:SHORT\s+)?NEAR\s+([\d.]+)', 'REJECTION'),
        (r'BOUNCE\s+(?:FROM\s+)?([\d.]+)', 'BOUNCE'),
        (r'AGGRESSIVE\s+BREAKOUT', 'AGGRESSIVE_BREAKOUT'),
        (r'CONSERVATIVE\s+BREAKOUT', 'CONSERVATIVE_BREAKOUT'),
        (r'AGGRESSIVE\s+BREAKDOWN', 'AGGRESSIVE_BREAKDOWN'),
        (r'CONSERVATIVE\s+BREAKDOWN', 'CONSERVATIVE_BREAKDOWN')
    ]
    
    for pattern, signal_type in signal_patterns:
        matches = re.finditer(pattern, text_upper)
        for match in matches:
            signals.append(signal_type)
    
    return list(set(signals))  # Remove duplicates


def extract_bias_from_section(text: str) -> Optional[str]:
    """
    Extract trading bias from section text.
    
    Args:
        text: Section text to analyze
        
    Returns:
        Optional[str]: Extracted bias (BULLISH, BEARISH, NEUTRAL)
    """
    text_lower = text.lower()
    
    # Bias indicators
    bullish_indicators = [
        'bullish', 'bull', 'breakout', 'upside', 'higher', 'bounce', 'support'
    ]
    
    bearish_indicators = [
        'bearish', 'bear', 'breakdown', 'downside', 'lower', 'rejection', 'resistance'
    ]
    
    bullish_count = sum(1 for indicator in bullish_indicators if indicator in text_lower)
    bearish_count = sum(1 for indicator in bearish_indicators if indicator in text_lower)
    
    if bullish_count > bearish_count:
        return 'BULLISH'
    elif bearish_count > bullish_count:
        return 'BEARISH'
    else:
        return 'NEUTRAL'


def _extract_price_targets(text: str) -> List[float]:
    """
    Extract price targets from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List[float]: Extracted price targets
    """
    targets = []
    
    # Price patterns with target indicators
    target_patterns = [
        r'🔼\s*([\d.]+)',  # Up arrow targets
        r'🔻\s*([\d.]+)',  # Down arrow targets
        r'Target\s+([\d.]+)',
        r'([\d.]+)(?=\s*(?:🔼|🔻))'
    ]
    
    for pattern in target_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                price = float(match.group(1))
                if 10.0 <= price <= 10000.0:  # Reasonable price range
                    targets.append(price)
            except (ValueError, IndexError):
                continue
    
    return sorted(list(set(targets)))


def _extract_price_levels(text: str) -> Dict[str, List[float]]:
    """
    Extract support and resistance levels from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict[str, List[float]]: Support and resistance levels
    """
    levels = {'support': [], 'resistance': []}
    
    # Look for bounce zones and key levels
    bounce_pattern = r'Bounce\s+(?:Zone|From)\s*[:\-]?\s*([\d.]+)(?:\s*[-–]\s*([\d.]+))?'
    matches = re.finditer(bounce_pattern, text, re.IGNORECASE)
    
    for match in matches:
        try:
            level1 = float(match.group(1))
            levels['support'].append(level1)
            
            if match.group(2):
                level2 = float(match.group(2))
                levels['support'].append(level2)
        except (ValueError, IndexError):
            continue
    
    return levels