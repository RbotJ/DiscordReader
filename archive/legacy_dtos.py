"""
Legacy DTOs - Archived from features/parsing/parser.py

These DTOs were replaced with the TradeSetup dataclass and structured field mappings.
Archived on: 2025-06-16
"""
from typing import List, Dict, Any, Optional, NamedTuple


class ParsedLevelDTO(NamedTuple):
    """Data transfer object for a parsed price level."""
    level_type: str  # entry, target, stop, bounce, rejection, breakout, breakdown
    direction: Optional[str]  # up, down, long, short
    trigger_price: float
    strategy: Optional[str]  # aggressive, conservative, normal
    confidence: Optional[float]  # 0.0 to 1.0
    description: Optional[str]


class ParsedSetupDTO(NamedTuple):
    """Data transfer object for a parsed trading setup."""
    ticker: str
    setup_type: Optional[str]  # breakout, breakdown, rejection, bounce
    bias_note: Optional[str]
    direction: Optional[str]  # bullish, bearish, neutral
    confidence_score: Optional[float]
    raw_content: str
    parsed_metadata: Optional[Dict[str, Any]]


class APlusSetupDTO(NamedTuple):
    """Legacy A+ specific setup DTO (if it existed)."""
    # This would have contained A+ specific fields
    pass