        """
        Event Channel Constants

        Defines flat string constants for PostgreSQL event logging.
        """

        # --- Discord Events ---
        DISCORD_MESSAGE_CHANNEL = "discord:message"
        DISCORD_SETUP_MESSAGE_CHANNEL = "discord:setup_message"
        DISCORD_RAW_MESSAGE_CHANNEL = "discord:raw_message"

        # --- Market Data Events ---
        TICKER_DATA_CHANNEL = "market:ticker_data"
        PRICE_ALERT_CHANNEL = "market:price_alert"
        CANDLE_PATTERN_CHANNEL = "market:candle_pattern"

        # --- Setup Events ---
        SETUP_CREATED_CHANNEL = "setup:created"
        SETUP_UPDATED_CHANNEL = "setup:updated"
        SETUP_TRIGGERED_CHANNEL = "setup:triggered"

        # --- Trade Events ---
        TRADE_EXECUTED_CHANNEL = "trade:executed"
        TRADE_FILLED_CHANNEL = "trade:filled"
        TRADE_CANCELED_CHANNEL = "trade:canceled"

        # --- System Events ---
        SYSTEM_CHANNEL = "system"
