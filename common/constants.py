"""
Constants Module

This module provides system-wide constants for the trading application.
"""
from enum import Enum, auto

# Trading hours (Eastern Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# Signal states
class SignalState(str, Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    ACTIVE = "active"  # Trade executed
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

# Signal categories
class SignalCategory(str, Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"

# Signal events
class SignalEvent(str, Enum):
    ADDED = "added"
    UPDATED = "updated"
    TRIGGERED = "trigger"
    TARGET_HIT = "target_hit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Trade directions
class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"

# Order types
class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

# Time in force
class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good 'til cancelled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill

# Option types
class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"

# Redis channels
class RedisChannel(str, Enum):
    # Market data channels
    PRICE_UPDATES = "prices:all"
    PRICE_UPDATES_PREFIX = "prices:"
    CANDLE_UPDATES = "candles:all"
    CANDLE_UPDATES_PREFIX = "candles:"
    
    # Signal channels
    SIGNAL_UPDATES = "signals:all"
    SIGNAL_UPDATES_PREFIX = "signals:"
    
    # Trade channels
    TRADE_UPDATES = "trades:all"
    TRADE_UPDATES_PREFIX = "trades:"
    
    # System channels
    SYSTEM_EVENTS = "system:events"
    
    # Account channels
    ACCOUNT_UPDATES = "account:updates"
    POSITION_UPDATES = "positions:updates"
    ORDER_UPDATES = "orders:updates"

# Timeframes
class Timeframe(str, Enum):
    ONE_MINUTE = "1Min"
    FIVE_MINUTES = "5Min"
    FIFTEEN_MINUTES = "15Min"
    ONE_HOUR = "1Hour"
    ONE_DAY = "1Day"

# Default risk parameters
DEFAULT_RISK_AMOUNT = 500.0  # Maximum risk per position in dollars
DEFAULT_POSITION_SIZE = 1  # Default number of contracts/shares
MAX_POSITIONS = 5  # Maximum number of concurrent positions

# API endpoints
API_PREFIX = "/api"
HEALTH_CHECK_ENDPOINT = f"{API_PREFIX}/health"
TICKERS_ENDPOINT = f"{API_PREFIX}/tickers"
ACCOUNT_ENDPOINT = f"{API_PREFIX}/account"
POSITIONS_ENDPOINT = f"{API_PREFIX}/positions"
CANDLES_ENDPOINT = f"{API_PREFIX}/candles"
SIGNALS_ENDPOINT = f"{API_PREFIX}/signals"
ORDERS_ENDPOINT = f"{API_PREFIX}/orders"