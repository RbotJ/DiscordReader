"""
Common Models and Data Transfer Objects (DTOs)

This module defines common data structures and DTOs used across
different components of the application.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union


@dataclass
class TickerSetupDTO:
    """Data Transfer Object for ticker setup information."""
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
    """Data Transfer Object for trade signal information."""
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
    """Data Transfer Object for candle pattern information."""
    ticker: str
    date: date
    pattern_type: str  # "engulfing", "doji", etc.
    direction: str  # "bullish", "bearish"
    price: float
    volume: float
    strength: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PriceAlertDTO:
    """Data Transfer Object for price alert information."""
    ticker: str
    target_price: float
    alert_type: str  # "above", "below", "cross"
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradeDTO:
    """Data Transfer Object for trade information."""
    ticker: str
    order_type: str  # "market", "limit", "stop", "stop_limit"
    side: str  # "buy", "sell"
    quantity: int
    price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"  # "day", "gtc", "ioc", "fok"
    extended_hours: bool = False
    client_order_id: Optional[str] = None
    setup_id: Optional[int] = None
    signal_id: Optional[int] = None
    status: str = "new"  # "new", "filled", "partially_filled", "canceled", "rejected"
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    filled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DiscordMessageDTO:
    """Data Transfer Object for Discord message information."""
    message_id: str
    channel_id: str
    author_id: str
    content: str
    created_at: datetime
    is_setup: bool = False
    processed: bool = False
    embed_data: Optional[Dict[str, Any]] = None
    
    
@dataclass
class MarketDataDTO:
    """Data Transfer Object for market data information."""
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = "alpaca"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    
@dataclass
class Signal:
    """Data Transfer Object for trading signals."""
    ticker: str
    side: str  # "buy", "sell"
    timestamp: datetime
    price: Optional[float] = None
    reason: Optional[str] = None
    confidence: float = 0.0
    source: str = "system"
    

@dataclass
class TradeSetupMessage:
    """Data Transfer Object for trade setup messages."""
    message_id: str
    content: str
    author: str
    channel_id: str
    date: date
    setups: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    
@dataclass
class TickerSetup:
    """Data Transfer Object for ticker setup information with trade details."""
    ticker: str
    price_target: Optional[float]
    setup_type: str
    direction: str  # "bullish", "bearish", "neutral"
    confidence: float = 0.5
    source: str = "discord"
    timeframe: str = "day"  # "day", "hour", "week"
    active: bool = True
    message_ref: Optional[str] = None
    date: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    
@dataclass 
class Bias:
    """Data Transfer Object for market bias."""
    direction: str  # "bullish", "bearish", "neutral" 
    timeframe: str  # "day", "hour", "week"
    confidence: float
    reason: str
    source: str
    date: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.utcnow)