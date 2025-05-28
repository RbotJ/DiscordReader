"""
New Schema Models Package

This package contains the redesigned database models for improved setup parsing.
These models replace the old fragmented approach with a clean, normalized schema.

Models:
- DiscordChannel: Manages Discord channels for monitoring
- DiscordMessage: Stores raw Discord messages 
- TradeSetup: High-level ticker setup information per trading day
- ParsedLevel: Individual price levels and trading strategies

Migration Status: Ready for Alembic migration
Deprecates: trade_setups, ticker_setups, setup_messages tables
"""

from .discord_channels import DiscordChannel
from .discord_messages import DiscordMessage  
from .trade_setups import TradeSetup
from .parsed_levels import ParsedLevel

__all__ = [
    'DiscordChannel',
    'DiscordMessage', 
    'TradeSetup',
    'ParsedLevel'
]

# Version info for migration tracking
__version__ = '1.0.0'
__migration_target__ = 'new_setup_parsing_schema'