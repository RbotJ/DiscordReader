"""
Discord Alerts Package

This package provides functionality for sending alerts to Discord channels
based on trading signals and events.
"""

from features.alerts.discord.channel_manager import ChannelManager, setup as setup_channel_manager
from features.alerts.discord.publisher import AlertPublisher, AlertTypes, setup as setup_publisher
from features.alerts.discord.formatter import AlertFormatter

__all__ = [
    'ChannelManager',
    'AlertPublisher',
    'AlertTypes',
    'AlertFormatter',
    'setup'
]

def setup(bot):
    """
    Set up all Discord alert components
    
    Args:
        bot: Discord bot instance
    """
    # Setup channel manager first
    setup_channel_manager(bot)
    
    # Then setup publisher which depends on channel manager
    setup_publisher(bot)