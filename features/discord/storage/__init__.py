"""
Discord Storage Module

This module provides functionality for storing and retrieving Discord messages
in the PostgreSQL database.
"""
from features.discord.storage.messages import (
    store_message,
    get_latest_message,
    get_message_history,
    get_message_count,
    get_message_stats
)

__all__ = [
    'store_message',
    'get_latest_message',
    'get_message_history',
    'get_message_count',
    'get_message_stats'
]