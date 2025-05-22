"""Event channel definitions for PostgreSQL-based event system"""

class EventChannels:
    """Event channel names"""
    SETUP_CREATED = "setup.created"
    SIGNAL_TRIGGERED = "signal.triggered"
    TRADE_EXECUTED = "trade.executed"
    MARKET_PRICE_UPDATE = "market.price_update"
    NOTIFICATIONS = "notifications"
    DISCORD_SETUP_MESSAGE = "discord.setup_message"
    POSITION_UPDATE = "position.update"
    ORDER_UPDATE = "order.update"
    DISCORD_BOT_STATUS = "discord.bot_status"