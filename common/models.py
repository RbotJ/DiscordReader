from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime


class SignalCategory(str, Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"


class Aggressiveness(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"


class ComparisonType(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"
    RANGE = "range"


class BiasDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class BiasFlip(BaseModel):
    direction: BiasDirection
    price_level: float


class Signal(BaseModel):
    category: SignalCategory
    aggressiveness: Aggressiveness = Aggressiveness.NONE
    comparison: ComparisonType
    trigger: Union[float, List[float]]
    targets: List[float]


class Bias(BaseModel):
    direction: BiasDirection
    condition: ComparisonType
    price: float
    flip: Optional[BiasFlip] = None


class TickerSetup(BaseModel):
    symbol: str
    signals: List[Signal]
    bias: Optional[Bias] = None


class TradeSetupMessage(BaseModel):
    date: date
    raw_text: str
    setups: List[TickerSetup]
    source: str = "unknown"
    created_at: datetime = Field(default_factory=datetime.now)


class OptionsContract(BaseModel):
    symbol: str
    underlying: str
    expiration_date: date
    strike: float
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class TradeOrder(BaseModel):
    symbol: str
    quantity: int
    side: str  # 'buy' or 'sell'
    type: str  # 'market', 'limit', etc.
    time_in_force: str  # 'day', 'gtc', etc.
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    extended_hours: bool = False
    client_order_id: Optional[str] = None
    order_class: Optional[str] = None  # 'simple', 'bracket', 'oco', 'oto'
    take_profit: Optional[Dict[str, Any]] = None
    stop_loss: Optional[Dict[str, Any]] = None


class Position(BaseModel):
    symbol: str
    quantity: int
    avg_entry_price: float
    side: str  # 'long' or 'short'
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float
    lastday_price: float
    change_today: float


class MarketData(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    previous_close: Optional[float] = None
    volume: Optional[int] = None
