"""
Common constants for the trading application.

This module defines constants used throughout the application.
"""

# Redis channels
PRICE_UPDATE_CHANNEL = "market.price_updates"
CANDLE_UPDATE_CHANNEL = "market.candle_updates"
TICKER_SIGNAL_CHANNEL = "market.ticker_signals"
STRATEGY_CHANNEL = "strategy.events"
EXECUTION_CHANNEL = "execution.events"
ACCOUNT_UPDATE_CHANNEL = "account.updates"
POSITION_UPDATE_CHANNEL = "position.updates"
NOTIFICATION_CHANNEL = "notifications"
SYSTEM_EVENTS_CHANNEL = "system.events"

# Ticker status values
TICKER_WATCHING = "watching"
TICKER_TRIGGERED = "triggered"
TICKER_TRADING = "trading"
TICKER_COMPLETED = "completed"
TICKER_FAILED = "failed"

# Signal types
SIGNAL_BREAKOUT = "breakout"
SIGNAL_BREAKDOWN = "breakdown"
SIGNAL_REJECTION = "rejection"
SIGNAL_BOUNCE = "bounce"

# Trade directions
TRADE_DIRECTION_LONG = "long"
TRADE_DIRECTION_SHORT = "short"

# Option types
OPTION_TYPE_CALL = "call"
OPTION_TYPE_PUT = "put"

# Exit types
EXIT_TYPE_STOP = "stop"
EXIT_TYPE_TARGET = "target"
EXIT_TYPE_BIAS_FLIP = "bias_flip"
EXIT_TYPE_EOD = "end_of_day"
EXIT_TYPE_MANUAL = "manual"

# Cache expiry times (in seconds)
CACHE_EXPIRY_SHORT = 60  # 1 minute
CACHE_EXPIRY_MEDIUM = 300  # 5 minutes
CACHE_EXPIRY_LONG = 3600  # 1 hour

# Timeframes
TIMEFRAME_1M = "1m"   # 1 minute
TIMEFRAME_5M = "5m"   # 5 minutes
TIMEFRAME_15M = "15m"  # 15 minutes
TIMEFRAME_1H = "1h"   # 1 hour
TIMEFRAME_1D = "1d"   # 1 day

# Default values
DEFAULT_STOP_PERCENTAGE = 0.02  # 2% stop loss
DEFAULT_TARGET_PERCENTAGES = [0.01, 0.02, 0.05]  # 1%, 2%, 5% targets
DEFAULT_MAX_DRAWDOWN = 500.0  # $500 max drawdown
DEFAULT_CONTRACT_SIZE = 1  # 1 contract per ticker
DEFAULT_TIMEFRAME = TIMEFRAME_5M  # Default to 5-minute timeframe