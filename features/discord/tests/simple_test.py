"""
Simple Discord Test Module

This module provides simple test functions for the Discord client integration.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional

from features.discord.client.api import get_discord_client
from features.discord.utils.environment import validate_discord_env, get_channel_id

logger = logging.getLogger(__name__)

async def test_discord_connection() -> bool:
    """
    Test the Discord connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = get_discord_client()
        connected = await client.connect()
        
        if connected:
            logger.info("Discord connection successful")
            await client.disconnect()
            return True
        else:
            logger.error("Failed to connect to Discord")
            return False
    except Exception as e:
        logger.error(f"Error testing Discord connection: {e}")
        return False

async def fetch_test_message(limit: int = 1) -> List[Dict[str, Any]]:
    """
    Fetch a test message from the Discord test channel.
    
    Args:
        limit: Maximum number of messages to fetch
        
    Returns:
        List of message dictionaries
    """
    try:
        if not validate_discord_env():
            logger.error("Discord environment variables not properly configured")
            return []
            
        client = get_discord_client()
        connected = await client.connect()
        
        if not connected:
            logger.error("Failed to connect to Discord")
            return []
            
        messages = await client.fetch_messages(channel_type='test', limit=limit)
        
        await client.disconnect()
        return messages
    except Exception as e:
        logger.error(f"Error fetching test message: {e}")
        return []

async def send_test_message(content: str) -> Optional[Dict[str, Any]]:
    """
    Send a test message to the Discord test channel.
    
    Args:
        content: Message content
        
    Returns:
        Message dictionary or None if failed
    """
    try:
        if not validate_discord_env():
            logger.error("Discord environment variables not properly configured")
            return None
            
        client = get_discord_client()
        connected = await client.connect()
        
        if not connected:
            logger.error("Failed to connect to Discord")
            return None
            
        message = await client.send_message(content, channel_type='test')
        
        await client.disconnect()
        return message
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return None

def run_simple_test():
    """
    Run a simple test of the Discord integration.
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Test connection
        connection_ok = loop.run_until_complete(test_discord_connection())
        if not connection_ok:
            logger.error("Discord connection test failed")
            return False
            
        # Test fetching messages
        messages = loop.run_until_complete(fetch_test_message())
        if not messages:
            logger.warning("No test messages found")
        else:
            logger.info(f"Found {len(messages)} test messages")
            
        # Don't test sending messages by default to avoid spam
        
        return True
    except Exception as e:
        logger.error(f"Error running Discord tests: {e}")
        return False
    finally:
        loop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_simple_test()
    print(f"Discord tests {'passed' if success else 'failed'}")