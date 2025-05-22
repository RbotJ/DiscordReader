"""
Event System Constants

This module defines constants for the event system to ensure consistent
event channel names across the application.
"""
import enum

# Discord event channels
DISCORD_MESSAGE_CHANNEL = "discord:message"
DISCORD_SETUP_MESSAGE_CHANNEL = "discord:setup_message"
DISCORD_RAW_MESSAGE_CHANNEL = "discord:raw_message"

# Market data event channels
TICKER_DATA_CHANNEL = "market:ticker_data"
PRICE_ALERT_CHANNEL = "market:price_alert"
CANDLE_PATTERN_CHANNEL = "market:candle_pattern"

# Setup event channels
SETUP_CREATED_CHANNEL = "setup:created"
SETUP_UPDATED_CHANNEL = "setup:updated"
SETUP_TRIGGERED_CHANNEL = "setup:triggered"

# Trade event channels
TRADE_EXECUTED_CHANNEL = "trade:executed"
TRADE_FILLED_CHANNEL = "trade:filled"
TRADE_CANCELED_CHANNEL = "trade:canceled"

# System event channels
SYSTEM_CHANNEL = "system"

# Channel enum for compatibility
class EventChannels(enum.Enum):
    """Enumeration of event channels."""
    # Core system events
    SYSTEM = SYSTEM_CHANNEL
    # Discord-related events
    DISCORD_MESSAGE = DISCORD_MESSAGE_CHANNEL
    DISCORD_SETUP_MESSAGE = DISCORD_SETUP_MESSAGE_CHANNEL
    DISCORD_RAW_MESSAGE = DISCORD_RAW_MESSAGE_CHANNEL
    # Market data events
    TICKER_DATA = TICKER_DATA_CHANNEL
    PRICE_ALERT = PRICE_ALERT_CHANNEL
    CANDLE_PATTERN = CANDLE_PATTERN_CHANNEL
    # Setup-related events
    SETUP_CREATED = SETUP_CREATED_CHANNEL
    SETUP_UPDATED = SETUP_UPDATED_CHANNEL
    SETUP_TRIGGERED = SETUP_TRIGGERED_CHANNEL
    # Trade-related events
    TRADE_EXECUTED = TRADE_EXECUTED_CHANNEL
    TRADE_FILLED = TRADE_FILLED_CHANNEL
    TRADE_CANCELED = TRADE_CANCELED_CHANNEL

# Mapping between enum and channel names for backwards compatibility
class EventChannelMap:
    """Provides mapping between event enum and channel names."""
    
    @staticmethod
    def get_channel_name(channel_enum):
        """
        Convert an EventChannels enum to a channel name string.
        
        Args:
            channel_enum: The enum value from common.events.EventChannels
            
        Returns:
            str: The corresponding channel name
        """
        # Import here to avoid circular imports
        from common.events import EventChannels
        
        channel_map = {
            EventChannels.SYSTEM: SYSTEM_CHANNEL,
            EventChannels.DISCORD_MESSAGE: DISCORD_MESSAGE_CHANNEL,
            EventChannels.DISCORD_SETUP_MESSAGE: DISCORD_SETUP_MESSAGE_CHANNEL,
            EventChannels.TICKER_DATA: TICKER_DATA_CHANNEL,
            EventChannels.PRICE_ALERT: PRICE_ALERT_CHANNEL,
            EventChannels.CANDLE_PATTERN: CANDLE_PATTERN_CHANNEL,
            EventChannels.SETUP_CREATED: SETUP_CREATED_CHANNEL,
            EventChannels.SETUP_UPDATED: SETUP_UPDATED_CHANNEL,
            EventChannels.SETUP_TRIGGERED: SETUP_TRIGGERED_CHANNEL,
            EventChannels.TRADE_EXECUTED: TRADE_EXECUTED_CHANNEL,
            EventChannels.TRADE_FILLED: TRADE_FILLED_CHANNEL,
            EventChannels.TRADE_CANCELED: TRADE_CANCELED_CHANNEL,
        }
        
        return channel_map.get(channel_enum, str(channel_enum))