"""
Common Models Module

This module defines the data transfer objects (DTOs) and common models
used across the application.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Set, Tuple, Union


# Enum definitions
class SignalCategory(Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"


class Aggressiveness(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"


class ComparisonType(Enum):
    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"
    RANGE = "range"


class BiasDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


# Data transfer objects
@dataclass
class BiasFlip:
    """Represents a bias flip condition in a trading setup."""
    direction: BiasDirection
    price_level: float


@dataclass
class Bias:
    """Represents a market bias for a ticker."""
    direction: BiasDirection
    condition: ComparisonType
    price: float
    flip: Optional[BiasFlip] = None


@dataclass
class Signal:
    """Represents a trading signal for a ticker."""
    category: SignalCategory
    comparison: ComparisonType
    trigger: Union[float, Tuple[float, float]]
    targets: Set[float]
    aggressiveness: Aggressiveness = Aggressiveness.NONE


@dataclass
class TickerSetup:
    """Represents a trading setup for a specific ticker symbol."""
    symbol: str
    signals: List[Signal] = field(default_factory=list)
    bias: Optional[Bias] = None
    text: Optional[str] = None


@dataclass
class TradeSetupMessage:
    """Represents a trading setup message containing one or more ticker setups."""
    raw_text: str
    date: date
    source: str = "unknown"
    setups: List[TickerSetup] = field(default_factory=list)
    created_at: Optional[datetime] = None