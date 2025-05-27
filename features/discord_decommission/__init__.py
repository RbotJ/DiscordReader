"""
Discord Module

This module provides integration with Discord for messaging and notifications.
"""
import logging
from typing import Dict, Any, Optional, List

from features.discord.utils import (
    validate_discord_env,
    get_environment_status
)
from features.discord.client import (
    get_discord_client,
    DiscordClient,
    fetch_latest_message
)
from features.discord.storage import (
    store_message,
    get_latest_message,
    get_message_history,
    get_message_count,
    get_message_stats,
    init_db
)

logger = logging.getLogger(__name__)

def init_discord() -> bool:
    """
    Initialize the Discord integration.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    # Check environment configuration
    env_status = get_environment_status()
    missing_vars = [var for var, status in env_status.items() if not status]
    
    if missing_vars:
        logger.warning(f"Discord environment not fully configured. Missing: {', '.join(missing_vars)}")
        
    # Validate required environment variables
    if not validate_discord_env():
        return False
    
    # Initialize database components
    init_db()
    
    return True

__all__ = [
    # Main initialization
    'init_discord',
    
    # Client functions
    'get_discord_client',
    'DiscordClient',
    'fetch_latest_message',
    
    # Storage functions
    'store_message',
    'get_latest_message',
    'get_message_history',
    'get_message_count',
    'get_message_stats',
    
    # Utility functions
    'validate_discord_env',
    'get_environment_status'
]