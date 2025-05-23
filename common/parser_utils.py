"""
Parser Utilities

Consolidated text processing functions for trading setup message parsing.
Eliminates duplications across multiple parser modules by providing a
single source of truth for common parsing operations.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TickerSection:
    """Represents a parsed ticker section from a message."""
    ticker: str
    content: str
    start_position: int
    end_position: int


@dataclass
class ParsedSignal:
    """Represents a parsed trading signal."""
    signal_type: str
    price_level: Optional[float]
    confidence: float
    direction: str
    conditions: List[str]


@dataclass
class ParsedBias:
    """Represents a parsed market bias."""
    direction: str
    timeframe: str
    price_level: Optional[float]
    conditions: List[str]


def normalize_text(text: str) -> str:
    """
    Normalize text for consistent parsing by removing extra whitespace,
    standardizing formatting, and cleaning up common irregularities.
    
    Args:
        text: Raw text to normalize
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize line breaks
    normalized = re.sub(r'\s+', ' ', text.strip())
    
    # Standardize ticker symbols (ensure uppercase)
    normalized = re.sub(r'\$([a-zA-Z]+)', lambda m: f'${m.group(1).upper()}', normalized)
    
    # Standardize price formatting
    normalized = re.sub(r'\$\s+(\d+)', r'$\1', normalized)
    
    # Clean up common formatting issues
    normalized = re.sub(r'\s+([,.!?])', r'\1', normalized)
    normalized = re.sub(r'([,.!?])\s*([a-zA-Z])', r'\1 \2', normalized)
    
    return normalized


def extract_ticker_sections(text: str) -> List[TickerSection]:
    """
    Extract individual ticker sections from a multi-ticker message.
    
    Args:
        text: Normalized message text
        
    Returns:
        List of TickerSection objects containing parsed ticker information
    """
    sections = []
    normalized_text = normalize_text(text)
    
    # Pattern to identify ticker symbols
    ticker_pattern = r'\$([A-Z]{1,5})\b'
    ticker_matches = list(re.finditer(ticker_pattern, normalized_text))
    
    if not ticker_matches:
        return sections
    
    for i, match in enumerate(ticker_matches):
        ticker = match.group(1)
        start_pos = match.start()
        
        # Determine end position (start of next ticker or end of text)
        if i + 1 < len(ticker_matches):
            end_pos = ticker_matches[i + 1].start()
        else:
            end_pos = len(normalized_text)
        
        # Extract the content for this ticker
        content = normalized_text[start_pos:end_pos].strip()
        
        sections.append(TickerSection(
            ticker=ticker,
            content=content,
            start_position=start_pos,
            end_position=end_pos
        ))
    
    return sections


def process_ticker_sections(sections: List[TickerSection]) -> Dict[str, Dict[str, Any]]:
    """
    Process ticker sections to extract trading information for each ticker.
    
    Args:
        sections: List of TickerSection objects to process
        
    Returns:
        Dictionary mapping ticker symbols to their parsed information
    """
    processed = {}
    
    for section in sections:
        try:
            ticker_info = {
                'ticker': section.ticker,
                'raw_content': section.content,
                'signals': extract_signal_from_section(section.content),
                'bias': extract_bias_from_section(section.content),
                'price_levels': _extract_price_levels(section.content),
                'timeframes': _extract_timeframes(section.content),
                'setup_type': _classify_setup_type(section.content)
            }
            
            processed[section.ticker] = ticker_info
            
        except Exception as e:
            logger.error(f"Error processing section for {section.ticker}: {e}")
            processed[section.ticker] = {
                'ticker': section.ticker,
                'raw_content': section.content,
                'error': str(e)
            }
    
    return processed


def extract_signal_from_section(content: str) -> Optional[ParsedSignal]:
    """
    Extract trading signal information from a ticker section.
    
    Args:
        content: Text content for a specific ticker
        
    Returns:
        ParsedSignal object if signal found, None otherwise
    """
    if not content:
        return None
    
    content_lower = content.lower()
    
    # Signal type patterns
    signal_patterns = {
        'buy': r'\b(buy|long|call|bullish)\b',
        'sell': r'\b(sell|short|put|bearish)\b',
        'hold': r'\b(hold|wait|watch)\b',
        'breakout': r'\b(breakout|break\s*out|above)\b',
        'breakdown': r'\b(breakdown|break\s*down|below)\b'
    }
    
    signal_type = None
    for sig_type, pattern in signal_patterns.items():
        if re.search(pattern, content_lower):
            signal_type = sig_type
            break
    
    if not signal_type:
        return None
    
    # Extract price level
    price_level = _extract_primary_price(content)
    
    # Determine direction
    direction = 'bullish' if signal_type in ['buy', 'long', 'call', 'breakout'] else 'bearish'
    
    # Calculate confidence based on signal clarity
    confidence = _calculate_signal_confidence(content, signal_type)
    
    # Extract conditions
    conditions = _extract_conditions(content)
    
    return ParsedSignal(
        signal_type=signal_type,
        price_level=price_level,
        confidence=confidence,
        direction=direction,
        conditions=conditions
    )


def extract_bias_from_section(content: str) -> Optional[ParsedBias]:
    """
    Extract market bias information from a ticker section.
    
    Args:
        content: Text content for a specific ticker
        
    Returns:
        ParsedBias object if bias found, None otherwise
    """
    if not content:
        return None
    
    content_lower = content.lower()
    
    # Bias direction patterns
    bias_patterns = {
        'bullish': r'\b(bullish|bull|upside|higher|above)\b',
        'bearish': r'\b(bearish|bear|downside|lower|below)\b',
        'neutral': r'\b(neutral|sideways|range)\b'
    }
    
    direction = None
    for bias_dir, pattern in bias_patterns.items():
        if re.search(pattern, content_lower):
            direction = bias_dir
            break
    
    if not direction:
        return None
    
    # Extract timeframe
    timeframe = _extract_timeframe(content)
    
    # Extract price level for bias
    price_level = _extract_primary_price(content)
    
    # Extract conditions
    conditions = _extract_conditions(content)
    
    return ParsedBias(
        direction=direction,
        timeframe=timeframe or 'intraday',
        price_level=price_level,
        conditions=conditions
    )


def _extract_price_levels(content: str) -> List[float]:
    """Extract all price levels mentioned in the content."""
    price_pattern = r'\$?(\d+(?:\.\d{2})?)'
    matches = re.findall(price_pattern, content)
    
    prices = []
    for match in matches:
        try:
            price = float(match)
            if 1 <= price <= 10000:  # Reasonable price range
                prices.append(price)
        except ValueError:
            continue
    
    return sorted(list(set(prices)))


def _extract_primary_price(content: str) -> Optional[float]:
    """Extract the primary/target price from content."""
    prices = _extract_price_levels(content)
    return prices[0] if prices else None


def _extract_timeframes(content: str) -> List[str]:
    """Extract timeframes mentioned in the content."""
    timeframe_patterns = {
        '1min': r'\b(1m|1\s*min)\b',
        '5min': r'\b(5m|5\s*min)\b',
        '15min': r'\b(15m|15\s*min)\b',
        '1hour': r'\b(1h|1\s*hour|hourly)\b',
        '4hour': r'\b(4h|4\s*hour)\b',
        'daily': r'\b(daily|day|1d)\b',
        'weekly': r'\b(weekly|week|1w)\b'
    }
    
    content_lower = content.lower()
    found_timeframes = []
    
    for timeframe, pattern in timeframe_patterns.items():
        if re.search(pattern, content_lower):
            found_timeframes.append(timeframe)
    
    return found_timeframes


def _extract_timeframe(content: str) -> Optional[str]:
    """Extract the primary timeframe from content."""
    timeframes = _extract_timeframes(content)
    return timeframes[0] if timeframes else None


def _classify_setup_type(content: str) -> str:
    """Classify the type of trading setup based on content."""
    content_lower = content.lower()
    
    setup_types = {
        'breakout': r'\b(breakout|break\s*out|resistance\s*break)\b',
        'breakdown': r'\b(breakdown|break\s*down|support\s*break)\b',
        'bounce': r'\b(bounce|support\s*hold|reversal)\b',
        'rejection': r'\b(rejection|resistance\s*hold|failed\s*break)\b',
        'range': r'\b(range|sideways|consolidation)\b',
        'trend': r'\b(trend|trending|momentum)\b'
    }
    
    for setup_type, pattern in setup_types.items():
        if re.search(pattern, content_lower):
            return setup_type
    
    return 'unknown'


def _extract_conditions(content: str) -> List[str]:
    """Extract trading conditions/requirements from content."""
    condition_patterns = [
        r'\bif\s+([^.!?]+)',
        r'\bwhen\s+([^.!?]+)',
        r'\babove\s+([^.!?]+)',
        r'\bbelow\s+([^.!?]+)',
        r'\bwith\s+([^.!?]+)'
    ]
    
    conditions = []
    for pattern in condition_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        conditions.extend([match.strip() for match in matches])
    
    return conditions[:5]  # Limit to 5 conditions


def _calculate_signal_confidence(content: str, signal_type: str) -> float:
    """Calculate confidence score for a signal based on content analysis."""
    confidence = 0.5  # Base confidence
    
    content_lower = content.lower()
    
    # Boost confidence for specific keywords
    confidence_boosters = {
        'strong': 0.2,
        'confirmed': 0.3,
        'clear': 0.2,
        'obvious': 0.2,
        'target': 0.1,
        'stop': 0.1
    }
    
    for keyword, boost in confidence_boosters.items():
        if keyword in content_lower:
            confidence += boost
    
    # Reduce confidence for uncertainty keywords
    uncertainty_words = ['maybe', 'possibly', 'might', 'could', 'uncertain']
    for word in uncertainty_words:
        if word in content_lower:
            confidence -= 0.1
    
    # Ensure confidence stays within bounds
    return max(0.0, min(1.0, confidence))