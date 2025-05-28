"""
Event Channel Constants

Defines flat string constants for PostgreSQL event logging.
"""

class EventChannels:
    """Event channel constants for the enhanced events system."""
    
    # --- Discord Events ---
    DISCORD_MESSAGE = "discord:message"
    DISCORD_SETUP_MESSAGE = "discord:setup_message"
    DISCORD_RAW_MESSAGE = "discord:raw_message"
    DISCORD_BOT = "discord:bot"

    # --- Ingestion Events ---
    INGESTION_MESSAGE = "ingestion:message"
    INGESTION_BATCH = "ingestion:batch"
    INGESTION_STATUS = "ingestion:status"
    
    # --- Parsing Events ---
    PARSING_SETUP = "parsing:setup"
    PARSING_TICKER = "parsing:ticker"
    PARSING_LEVEL = "parsing:level"
    
    # --- Alert Events ---
    ALERT_PRICE = "alert:price"
    ALERT_SETUP = "alert:setup"
    ALERT_SYSTEM = "alert:system"

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
    
    # --- Bot Lifecycle Events ---
    BOT_STARTUP = "bot:startup"
    BOT_SHUTDOWN = "bot:shutdown"
    BOT_ERROR = "bot:error"

    # --- System Events ---
    SYSTEM = "system"

class EventTypes:
    """Event type constants for enhanced structured logging."""
    
    # Discord events
    DISCORD_RECEIVED = "discord.message.received"
    DISCORD_PROCESSED = "discord.message.processed"
    BOT_CONNECTED = "bot.connected"
    BOT_DISCONNECTED = "bot.disconnected"
    CHANNEL_SCANNED = "bot.channel.scanned"
    
    # Ingestion events
    MESSAGE_STORED = "ingestion.message.stored"
    BATCH_PROCESSED = "ingestion.batch.processed"
    CATCHUP_STARTED = "ingestion.catchup.started"
    CATCHUP_COMPLETED = "ingestion.catchup.completed"
    
    # Parsing events
    SETUP_PARSED = "parsing.setup.parsed"
    SETUP_SAVED = "parsing.setup.saved"
    TICKER_EXTRACTED = "parsing.ticker.extracted"
    LEVEL_IDENTIFIED = "parsing.level.identified"
    PARSE_FAILED = "parsing.failed"
    
    # Alert events
    PRICE_ALERT_TRIGGERED = "alert.price.triggered"
    SETUP_ALERT_SENT = "alert.setup.sent"
    SYSTEM_ALERT_RAISED = "alert.system.raised"
    
    # Setup events
    SETUP_CREATED = "setup.created"
    SETUP_UPDATED = "setup.updated"
    SETUP_TRIGGERED = "setup.triggered"
    
    # Signal events
    SIGNAL_TRIGGERED = "signal.triggered"
    SIGNAL_COMPLETED = "signal.completed"
    SIGNAL_CREATED = "signal.created"
    
    # Trade events
    TRADE_EXECUTED = "trade.executed"
    TRADE_FILLED = "trade.filled"
    
    # System events
    ERROR = "system.error"
    WARNING = "system.warning"
    INFO = "system.info"
