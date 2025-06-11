"""
Blueprint Registry

Centralized blueprint configuration for the A+ Trading application.
This module defines all blueprints that should be registered with Flask,
including both API routes and dashboard routes.
"""

# Blueprint registry: (name, module_path, attribute_name)
BLUEPRINT_REGISTRY = [
    # API Blueprints
    ("market", "features.market.api_routes", "bp"),
    ("execution", "features.execution.api_routes", "bp"),
    ("options", "features.options.api_routes", "bp"),
    ("account", "features.account.api_routes", "bp"),
    ("alpaca", "features.alpaca.api", "alpaca_bp"),
    ("parsing_api", "features.parsing.api", "parsing_bp"),
    ("setups", "features.setups.api", "setups_bp"),
    
    # Dashboard Blueprints
    ("parsing_dashboard", "features.parsing.dashboard", "parsing_bp"),
    ("discord_dashboard", "features.discord_bot.dashboard", "discord_bp"),
    ("channels_dashboard", "features.discord_channels.dashboard", "channels_bp"),
    ("ingestion_dashboard", "features.ingestion.dashboard", "ingest_bp"),
]

# Additional blueprints that require special handling
SPECIAL_BLUEPRINTS = [
    # Discord API blueprint is registered separately in register_feature_routes
    ("discord_api", "features.discord_bot.api", "discord_api_bp"),
]