"""
Discord Simple Test Module

This module provides simple test utilities for the Discord integration.
It allows testing the connection to Discord and sending test messages.
"""
import logging
import asyncio
from typing import Dict, Any, Optional

from features.discord.client.api import get_discord_client
from features.discord.utils.environment import validate_discord_env
from features.discord.storage.messages import store_message

logger = logging.getLogger(__name__)

async def test_discord_connection() -> bool:
    """
    Test the connection to Discord.
    
    Returns:
        bool: True if connected successfully, False otherwise
    """
    try:
        # Check environment variables
        if not validate_discord_env():
            logger.error("Cannot test Discord connection: Environment validation failed")
            return False
            
        # Connect to Discord
        client = get_discord_client()
        success = await client.connect()
        
        if success:
            logger.info("Discord connection test successful")
            return True
        else:
            logger.error("Discord connection test failed")
            return False
    except Exception as e:
        logger.error(f"Discord connection test failed with error: {e}")
        return False

async def fetch_test_message() -> Optional[Dict[str, Any]]:
    """
    Fetch a test message from Discord.
    
    Returns:
        Message dictionary or None if failed
    """
    try:
        # Check environment variables
        if not validate_discord_env():
            logger.error("Cannot fetch test message: Environment validation failed")
            return None
            
        # Connect to Discord and fetch message
        client = get_discord_client()
        if not await client.connect():
            logger.error("Cannot fetch test message: Connection failed")
            return None
            
        messages = await client.fetch_messages(channel_type='test', limit=1)
        if not messages:
            logger.warning("No test messages found")
            return None
            
        logger.info(f"Fetched test message: {messages[0]['content'][:50]}...")
        return messages[0]
    except Exception as e:
        logger.error(f"Failed to fetch test message: {e}")
        return None

async def send_test_message(content: str) -> bool:
    """
    Send a test message to Discord.
    
    Args:
        content: Message content
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Check environment variables
        if not validate_discord_env():
            logger.error("Cannot send test message: Environment validation failed")
            return False
            
        # Connect to Discord and send message
        client = get_discord_client()
        if not await client.connect():
            logger.error("Cannot send test message: Connection failed")
            return False
            
        message = await client.send_message(content, channel_type='test')
        if not message:
            logger.error("Failed to send test message")
            return False
            
        # Store message in database
        store_message(message)
        
        logger.info(f"Test message sent: {content[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to send test message: {e}")
        return False

def run_simple_test():
    """Run a simple test of Discord functionality."""
    try:
        loop = asyncio.get_event_loop()
        
        # Test connection
        if not loop.run_until_complete(test_discord_connection()):
            logger.error("Discord connection test failed")
            return False
            
        # Fetch test message
        message = loop.run_until_complete(fetch_test_message())
        if not message:
            logger.warning("Could not fetch test message")
        else:
            logger.info(f"Fetched message: {message['content'][:50]}...")
            
        # Send test message
        test_content = "A+ Trading Discord Test - " + datetime.now().isoformat()
        sent = loop.run_until_complete(send_test_message(test_content))
        if not sent:
            logger.error("Could not send test message")
            return False
            
        logger.info("Discord simple test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Discord simple test failed with error: {e}")
        return False

if __name__ == "__main__":
    from datetime import datetime
    logging.basicConfig(level=logging.INFO)
    run_simple_test()