"""
Schema Module

This module defines data transfer objects (DTOs) for passing data between layers.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Set, Tuple, Union

# Enum definitions for DTOs
class SignalCategoryDTO(Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"


class AggressivenessDTO(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"


class ComparisonTypeDTO(Enum):
    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"
    RANGE = "range"


class BiasDirectionDTO(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


# Data transfer objects
@dataclass
class BiasFlipDTO:
    """Represents a bias flip condition in a trading setup."""
    direction: BiasDirectionDTO
    price_level: float


@dataclass
class BiasDTO:
    """Represents a market bias for a ticker."""
    direction: BiasDirectionDTO
    condition: ComparisonTypeDTO
    price: float
    flip: Optional[BiasFlipDTO] = None


@dataclass
class SignalDTO:
    """Represents a trading signal for a ticker."""
    category: SignalCategoryDTO
    comparison: ComparisonTypeDTO
    trigger: Union[float, Tuple[float, float]]
    targets: Set[float]
    aggressiveness: AggressivenessDTO = AggressivenessDTO.NONE


@dataclass
class TickerSetupDTO:
    """Represents a trading setup for a specific ticker symbol."""
    symbol: str
    signals: List[SignalDTO] = field(default_factory=list)
    bias: Optional[BiasDTO] = None
    text: Optional[str] = None


@dataclass
class TradeSetupDTO:
    """Represents a trading setup message containing one or more ticker setups."""
    raw_text: str
    date: date
    source: str = "unknown"
    setups: List[TickerSetupDTO] = field(default_factory=list)
    created_at: Optional[datetime] = None