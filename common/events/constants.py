"""
Event System Constants

This module defines constants for the event system, including channel names.
"""

class EventChannels:
    """Event channel names used throughout the application."""
    
    # Discord related events
    DISCORD_MESSAGE = "discord.message"
    DISCORD_SETUP = "discord.setup"
    
    # Trade related events
    TRADE_EXECUTED = "trade.executed"
    TRADE_UPDATED = "trade.updated"
    
    # Setup related events
    SETUP_CREATED = "setup.created"
    SETUP_UPDATED = "setup.updated"
    
    # Ticker related events
    TICKER_DATA = "ticker.data"
    TICKER_PRICE = "ticker.price"
    
    # Alert related events
    ALERT_TRIGGERED = "alert.triggered"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_NOTIFICATION = "system.notification"