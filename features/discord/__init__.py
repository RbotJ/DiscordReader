"""
Discord Module

This module provides functionality for interacting with Discord,
including fetching and parsing messages for trading setups.
"""

# Import submodules for easier access
from features.discord.client import (
    init_discord_client,
    shutdown_discord_client,
    is_discord_available,
    register_message_handler,
    unregister_message_handler,
    fetch_recent_messages
)

from features.discord.message_parser import (
    parse_message,
    extract_tickers,
    detect_signal_type,
    detect_bias,
    validate_setup
)