"""
Discord Storage Module

This module provides storage functionality for Discord messages and related data.
"""
from features.discord.storage.messages import (
    store_message,
    get_latest_message,
    get_message_history,
    get_message_count,
    get_message_stats,
    init_db
)

__all__ = [
    'store_message',
    'get_latest_message',
    'get_message_history',
    'get_message_count',
    'get_message_stats',
    'init_db'
]