"""
Discord Integration Feature

This module handles integration with Discord for retrieving and processing messages.
"""
import os
import logging

# Create a logger for this module
logger = logging.getLogger(__name__)

def init_discord():
    """
    Initialize Discord integration by checking environment variables.
    
    Returns:
        True if successful, False otherwise
    """
    # Check for required environment variables
    token = os.environ.get("DISCORD_BOT_TOKEN")
    channel = os.environ.get("DISCORD_CHANNEL_ID")
    
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        return False
        
    if not channel:
        logger.error("DISCORD_CHANNEL_ID environment variable not set")
        return False
    
    logger.info("Discord integration initialized successfully")
    return True