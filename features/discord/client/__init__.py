"""
Discord Client Module

This module provides the Discord client API for interacting with Discord.
"""
from features.discord.client.api import (
    get_discord_client,
    DiscordClient,
    fetch_latest_message
)

__all__ = [
    'get_discord_client',
    'DiscordClient',
    'fetch_latest_message'
]