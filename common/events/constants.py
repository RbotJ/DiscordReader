"""
Event System Constants

This module defines constants used by the event system, including channel names
and event types.
"""

class EventChannels:
    """Event channel constants used for publishing and subscribing to events."""
    
    # Discord-related channels
    DISCORD_MESSAGE = "discord.message"
    DISCORD_SETUP = "discord.setup"
    
    # Setup-related channels
    SETUP_CREATED = "setup.created"
    SETUP_UPDATED = "setup.updated"
    
    # Trade-related channels
    TRADE_EXECUTED = "trade.executed"
    TRADE_FILLED = "trade.filled"
    TRADE_CANCELED = "trade.canceled"
    
    # Market data channels
    PRICE_UPDATE = "market.price_update"
    CANDLE_DETECTED = "market.candle_detected"
    
    # Alert channels
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_CREATED = "alert.created"
    
    # System channels
    SYSTEM_ERROR = "system.error"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"