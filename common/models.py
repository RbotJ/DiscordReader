from enum import Enum
from datetime import date, datetime
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

# Enumerations
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

class ComparisonType(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"
    RANGE = "range"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good 'til canceled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill

# Model classes
class BiasFlip(BaseModel):
    """Conditions for when a bias flips from bullish to bearish or vice versa"""
    new_direction: str
    condition: ComparisonType
    price: float

class Signal(BaseModel):
    """Trading signal extracted from A+ setup messages"""
    category: SignalCategory
    aggressiveness: Aggressiveness = Aggressiveness.NONE
    comparison: ComparisonType
    trigger: Union[float, List[float]]
    targets: List[float]

class Bias(BaseModel):
    """Market bias extracted from A+ setup messages"""
    direction: str             # bullish/bearish
    condition: ComparisonType  # above/below
    price: float
    flip: Optional[BiasFlip] = None

class TickerSetup(BaseModel):
    """Setup for a specific ticker/symbol"""
    symbol: str
    signals: List[Signal]
    bias: Optional[Bias] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    def is_triggered(self, current_price: float) -> bool:
        """Check if any signals are triggered based on current price"""
        for signal in self.signals:
            if self._is_signal_triggered(signal, current_price):
                return True
        return False
    
    def _is_signal_triggered(self, signal: Signal, price: float) -> bool:
        """Check if a specific signal is triggered based on current price"""
        if signal.comparison == ComparisonType.ABOVE:
            if isinstance(signal.trigger, float):
                return price > signal.trigger
            return False
        elif signal.comparison == ComparisonType.BELOW:
            if isinstance(signal.trigger, float):
                return price < signal.trigger
            return False
        elif signal.comparison == ComparisonType.NEAR:
            if isinstance(signal.trigger, float):
                # Within 0.5% of trigger price
                return abs(price - signal.trigger) / signal.trigger < 0.005
            return False
        elif signal.comparison == ComparisonType.RANGE:
            if isinstance(signal.trigger, list) and len(signal.trigger) == 2:
                return signal.trigger[0] <= price <= signal.trigger[1]
            return False
        return False

class TradeSetupMessage(BaseModel):
    """Complete trade setup message with multiple tickers"""
    date: date = Field(default_factory=lambda: date.today())
    raw_text: str
    setups: List[TickerSetup]
    created_at: datetime = Field(default_factory=datetime.now)

class OptionsContract(BaseModel):
    """Options contract details"""
    symbol: str
    underlying: str
    strike: float
    expiration: date
    option_type: str  # "call" or "put"
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

class Position(BaseModel):
    """Trading position details"""
    symbol: str
    quantity: float
    side: OrderSide
    average_price: float
    current_price: float
    unrealized_pl: float
    realized_pl: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    strategy: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Calculate position duration in days"""
        end_time = self.exit_time or datetime.now()
        return (end_time - self.entry_time).total_seconds() / 86400
    
    @property
    def pl_percent(self) -> float:
        """Calculate profit/loss percentage"""
        if self.average_price == 0:
            return 0
        pl = self.unrealized_pl if self.exit_time is None else self.realized_pl
        return (pl / (self.average_price * abs(self.quantity))) * 100

class Order(BaseModel):
    """Order details for execution"""
    symbol: str
    quantity: float
    side: OrderSide
    option_symbol: Optional[str] = None
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    client_order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Notification(BaseModel):
    """Notification message for alerts"""
    message: str
    level: str = "info"  # info, warning, error
    created_at: datetime = Field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None
