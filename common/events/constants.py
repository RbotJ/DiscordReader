"""
Event Constants

Constants for the event system in the trading application.
"""
from enum import Enum, auto


class EventChannels(str, Enum):
    """Channels for the event system"""
    DISCORD_SETUP_MESSAGE = "discord_setup_message"
    SETUP_CREATED = "setup_created"
    SETUP_UPDATED = "setup_updated"
    TRADE_EXECUTED = "trade_executed"
    SIGNAL_TRIGGERED = "signal_triggered"
    PRICE_ALERT = "price_alert"
    ERROR_NOTIFICATION = "error_notification"
    SYSTEM_STATUS = "system_status"