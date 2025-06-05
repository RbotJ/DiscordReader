"""
Common data models and DTOs for cross-slice communication.

These models provide standard data structures that can be shared
across vertical slices without creating direct dependencies.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal


@dataclass
class DiscordMessageDTO:
    """Data transfer object for Discord messages."""
    message_id: str
    channel_id: str
    author_id: str
    content: str
    timestamp: datetime
    guild_id: Optional[str] = None
    author_username: Optional[str] = None
    channel_name: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    embeds: Optional[List[Dict[str, Any]]] = None


@dataclass
class MarketDataDTO:
    """Data transfer object for market data."""
    symbol: str
    price: Decimal
    timestamp: datetime
    volume: Optional[int] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[float] = None


@dataclass
class TradingSignalDTO:
    """Data transfer object for trading signals."""
    signal_id: str
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float
    timestamp: datetime
    source: str
    price_target: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OrderDTO:
    """Data transfer object for order information."""
    order_id: str
    symbol: str
    quantity: int
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', etc.
    status: str
    timestamp: datetime
    filled_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    limit_price: Optional[Decimal] = None


@dataclass
class AccountDTO:
    """Data transfer object for account information."""
    account_id: str
    cash: Decimal
    portfolio_value: Decimal
    buying_power: Decimal
    day_trade_count: int
    pattern_day_trader: bool
    timestamp: datetime


@dataclass
class PositionDTO:
    """Data transfer object for position information."""
    symbol: str
    quantity: int
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    side: str  # 'long' or 'short'
    timestamp: datetime


@dataclass
class OptionContractDTO:
    """Data transfer object for options contract data."""
    symbol: str
    underlying_symbol: str
    expiration_date: str  # ISO format
    strike_price: Decimal
    option_type: str  # 'call' or 'put'
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: int
    open_interest: int
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


@dataclass
class EventDTO:
    """Data transfer object for system events."""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime
    correlation_id: Optional[str] = None
    channel: str = "default"


@dataclass
class AlertDTO:
    """Data transfer object for alerts and notifications."""
    alert_id: str
    alert_type: str
    message: str
    severity: str  # 'info', 'warning', 'error', 'critical'
    timestamp: datetime
    source: str
    target: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StrategyDTO:
    """Data transfer object for trading strategy information."""
    strategy_id: str
    name: str
    description: str
    status: str  # 'active', 'paused', 'stopped'
    performance: Dict[str, Any]
    parameters: Dict[str, Any]
    timestamp: datetime
    created_by: str


@dataclass
class RiskMetricsDTO:
    """Data transfer object for risk assessment metrics."""
    symbol: str
    position_size: Decimal
    risk_amount: Decimal
    risk_percent: float
    max_loss: Decimal
    timestamp: datetime
    probability_of_profit: Optional[float] = None
    expected_return: Optional[Decimal] = None
    sharpe_ratio: Optional[float] = None