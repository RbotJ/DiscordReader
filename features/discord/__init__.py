"""
Discord Integration Package

This package provides integration with Discord for the A+ Trading application,
including monitoring for trading setup messages and publishing notifications.
"""
import logging
import time
from features.discord.client import (
    initialize_discord_client, send_status_update, send_trade_alert,
    send_error_notification, is_discord_available, is_client_ready
)
from features.discord.setup_handler import register_discord_setup_handler

logger = logging.getLogger(__name__)

def init_discord():
    """Initialize Discord integration features."""
    if not is_discord_available:
        logger.warning("Discord integration disabled due to missing configuration")
        return False
    
    # Initialize the Discord client
    client_initialized = initialize_discord_client()
    if not client_initialized:
        logger.error("Failed to initialize Discord client")
        return False
    
    # Register the setup message handler
    register_discord_setup_handler()
    
    # Register command handlers
    try:
        from features.discord.commands import register_command_handlers
        register_command_handlers()
        logger.info("Discord command handlers registered")
    except Exception as e:
        logger.warning(f"Could not register Discord command handlers: {e}")
    
    # Give the client some time to connect
    logger.info("Waiting for Discord client to initialize...")
    max_wait = 10  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if is_client_ready():
            # Send startup message
            send_status_update("A+ Trading Bot has been restarted and is now online.")
            logger.info("Discord integration initialized and ready")
            return True
        time.sleep(0.5)
    
    logger.warning("Discord client didn't become ready in the expected time, but initialization will continue")
    logger.info("Discord integration initialized (client not yet ready)")
    return True