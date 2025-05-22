"""
Discord Feature Module

This module provides Discord integration for the A+ Trading application.
It includes functionality for connecting to Discord, fetching messages,
and parsing them for trade setups.
"""
import logging
from typing import Dict, Any, Optional, List
import asyncio

from features.discord.utils.environment import validate_discord_env
from features.discord.client.api import get_discord_client
from features.discord.storage.messages import store_message, get_latest_message

logger = logging.getLogger(__name__)

async def initialize_discord() -> bool:
    """
    Initialize Discord integration.
    
    Returns:
        bool: True if initialized successfully, False otherwise
    """
    try:
        # Check environment variables
        if not validate_discord_env():
            logger.error("Discord initialization failed: Environment validation failed")
            return False
            
        # Connect to Discord
        client = get_discord_client()
        success = await client.connect()
        
        if success:
            logger.info("Discord initialized successfully")
            return True
        else:
            logger.error("Discord initialization failed: Connection failed")
            return False
    except Exception as e:
        logger.error(f"Discord initialization failed: {e}")
        return False
        
async def fetch_latest_messages(channel_type: str = 'default', limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch latest messages from Discord.
    
    Args:
        channel_type: Type of channel to fetch from
        limit: Maximum number of messages to fetch
        
    Returns:
        List of message dictionaries
    """
    try:
        client = get_discord_client()
        messages = await client.fetch_messages(channel_type, limit)
        
        # Store messages in database
        for message in messages:
            store_message(message)
            
        return messages
    except Exception as e:
        logger.error(f"Failed to fetch latest messages: {e}")
        return []
        
def get_stored_messages(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get stored messages from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries
    """
    from features.discord.storage.messages import get_message_history
    return get_message_history(limit)
    
def get_latest_stored_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest stored message from the database.
    
    Returns:
        Message dictionary or None if not found
    """
    return get_latest_message()
    
def run_sync_operation(coroutine):
    """
    Run an asynchronous coroutine synchronously.
    
    Args:
        coroutine: Async coroutine to run
        
    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()
        
def init():
    """Initialize Discord integration synchronously."""
    return run_sync_operation(initialize_discord())
    
def fetch_messages(channel_type: str = 'default', limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch messages synchronously."""
    return run_sync_operation(fetch_latest_messages(channel_type, limit))