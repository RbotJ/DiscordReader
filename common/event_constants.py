"""
Event Channel Constants

Defines flat string constants for PostgreSQL event logging.
"""

class EventChannels:
    """Event channel constants for the unified events system."""
    
    # --- Discord Events ---
    DISCORD_MESSAGE = "discord:message"
    DISCORD_SETUP_MESSAGE = "discord:setup_message"
    DISCORD_RAW_MESSAGE = "discord:raw_message"

    # --- Market Data Events ---
    TICKER_DATA = "market:ticker_data"
    PRICE_ALERT = "market:price_alert"
    CANDLE_PATTERN = "market:candle_pattern"

    # --- Setup Events ---
    SETUP_CREATED = "setup:created"
    SETUP_UPDATED = "setup:updated"
    SETUP_TRIGGERED = "setup:triggered"

    # --- Trade Events ---
    TRADE_EXECUTED = "trade:executed"
    TRADE_FILLED = "trade:filled"
    TRADE_CANCELED = "trade:canceled"

    # --- System Events ---
    SYSTEM = "system"

class EventType:
    """Event type constants for structured logging."""
    
    # Setup events
    SETUP_PARSED = "setup_parsed"
    SETUP_SAVED = "setup_saved"
    SETUP_UPDATED = "setup_updated"
    SETUP_CREATED = "setup_created"
    
    # Signal events
    SIGNAL_TRIGGERED = "signal_triggered"
    SIGNAL_COMPLETED = "signal_completed"
    SIGNAL_CREATED = "signal_created"
    
    # Bias events
    BIAS_CREATED = "bias_created"
    
    # Trade events
    TRADE_EXECUTED = "trade_executed"
    TRADE_FILLED = "trade_filled"
    
    # Position events
    POSITION_UPDATED = "position_updated"
    
    # System events
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
