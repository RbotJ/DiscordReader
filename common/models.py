"""
models.py

Pydantic schemas and DTOs for the A+ Trading App.
Use these for serialization, validation, and agent-friendly task context.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import enum

# --- Enum Definitions (match SQLAlchemy for consistency) ---
class SignalCategoryEnum(str, enum.Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"

class AggressivenessEnum(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"

class ComparisonTypeEnum(str, enum.Enum):
    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"
    RANGE = "range"

class BiasDirectionEnum(str, enum.Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"

# --- Data Transfer Objects (DTOs) ---
@dataclass
class TradeSetupDTO:
    ticker: str
    date: date 
    price: Optional[float] = None
    setup_type: str = "unknown"
    context: str = ""
    source: str = "discord"
    active: bool = True
    executed: bool = False
    message_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TradeSignalDTO:
    ticker: str
    date: date
    signal_type: str  # "buy", "sell", "hold"
    price: Optional[float] = None
    expiration: Optional[date] = None
    strike_price: Optional[float] = None
    is_call: Optional[bool] = None
    quantity: int = 1
    setup_id: Optional[int] = None
    confidence: float = 0.0
    context: str = ""
    active: bool = True
    executed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CandlePatternDTO:
    ticker: str
    date: date
    pattern_type: str
    direction: str
    price: float
    volume: float
    strength: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PriceAlertDTO:
    ticker: str
    target_price: float
    alert_type: str  # "above", "below", "cross"
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TradeDTO:
    ticker: str
    order_type: str  # "market", "limit", "stop", "stop_limit"
    side: str  # "buy", "sell"
    quantity: int
    price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    extended_hours: bool = False
    client_order_id: Optional[str] = None
    setup_id: Optional[int] = None
    signal_id: Optional[int] = None
    status: str = "new"
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    filled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DiscordMessageDTO:
    message_id: str
    channel_id: str
    author_id: str
    content: str
    created_at: datetime
    is_setup: bool = False
    processed: bool = False
    embed_data: Optional[Dict[str, Any]] = None

@dataclass
class TradeSetupMessage:
    message_id: str
    content: str
    author: str
    channel_id: str
    date: date
    setups: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TickerSetupData:
    ticker: str
    price_target: Optional[float]
    setup_type: str
    direction: str
    confidence: float = 0.5
    source: str = "discord"
    timeframe: str = "day"
    active: bool = True
    message_ref: Optional[str] = None
    date: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class BiasFlip:
    direction: Optional[BiasDirectionEnum] = None
    price_level: Optional[float] = None
    condition: str = "cross"
    message: Optional[str] = None

@dataclass
class Bias:
    direction: str
    timeframe: str
    confidence: float
    reason: str
    source: str
    price: Optional[float] = None
    flip: Optional[BiasFlip] = None
    date: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Signal:
    ticker: str
    side: str
    timestamp: datetime
    price: Optional[float] = None
    reason: Optional[str] = None
    confidence: float = 0.0
    source: str = "system"
