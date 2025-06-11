"""
Blueprint Registry for Feature Registration

Centralized configuration for all feature blueprints following
vertical slice architecture principles.
"""

# Blueprint registration configuration
# Format: (name, module_path, attribute_name)
BLUEPRINT_CONFIGS = [
    ("market", "features.market.api_routes", "bp"),
    ("execution", "features.execution.api_routes", "bp"),
    ("options", "features.options.api_routes", "bp"),
    ("account", "features.account.api_routes", "bp"),
    ("alpaca", "features.alpaca.api", "alpaca_bp"),
    ("parsing_api", "features.parsing.api", "parsing_bp"),
    ("parsing_dashboard", "features.parsing.dashboard", "parsing_bp"),
    ("setups", "features.setups.api", "setups_bp"),
    ("discord_api", "features.discord_bot.api", "discord_api_bp"),
    # Dashboard blueprints
    ("discord_dashboard", "features.discord_bot.dashboard", "discord_bp"),
    ("ingestion_dashboard", "features.ingestion.dashboard", "ingest_bp"),
    ("channels_dashboard", "features.discord_channels.dashboard", "channels_bp"),
]

# Required environment variables for the application
REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SESSION_SECRET",
]

# Optional environment variables with defaults
OPTIONAL_ENV_VARS = {
    "ALPACA_API_KEY": "",
    "ALPACA_API_SECRET": "",
    "DISCORD_BOT_TOKEN": "",
    "ENABLE_DISCORD_BOT": "true",
    "ENABLE_LIVE_PRICE_STREAM": "false",
    "USE_LIVE_DATA": "false",
    "PAPER_TRADING": "true",
}