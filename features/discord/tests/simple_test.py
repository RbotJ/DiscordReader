"""
Simple Discord Test

This module provides a simple test for the Discord integration.
"""
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from features.discord.client import get_discord_client
from features.discord.storage import store_message, get_latest_message, get_message_count
from features.discord.utils import get_discord_token, get_channel_id, validate_discord_env

logger = logging.getLogger(__name__)

async def _test_connection_async():
    """Test connection to Discord API."""
    logger.info("Testing Discord connection...")
    client = get_discord_client()
    
    token = get_discord_token()
    if not token:
        logger.error("No Discord token available for testing")
        return False
    
    try:
        await client.login(token)
        logger.info("Successfully connected to Discord")
        await client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Discord: {e}")
        return False

async def _test_fetch_message_async():
    """Test fetching a message from Discord."""
    logger.info("Testing message fetching...")
    client = get_discord_client()
    
    token = get_discord_token()
    channel_id = get_channel_id()
    
    if not token:
        logger.error("No Discord token available for testing")
        return False
    
    if not channel_id:
        logger.error("No channel ID available for testing")
        return False
    
    try:
        # Login
        await client.login(token)
        
        # Get the channel
        channel = client.get_channel(int(channel_id))
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            await client.close()
            return False
        
        # Fetch a message
        messages = await channel.history(limit=1).flatten()
        if not messages:
            logger.warning(f"No messages found in channel {channel_id}")
            await client.close()
            return False
        
        message = messages[0]
        logger.info(f"Successfully fetched message: {message.content[:50]}...")
        
        # Store the message
        message_data = {
            'id': str(message.id),
            'content': message.content,
            'author': message.author.name,
            'author_id': str(message.author.id),
            'channel_id': str(message.channel.id),
            'channel_name': getattr(channel, 'name', 'direct-message'),
            'timestamp': message.created_at.isoformat()
        }
        
        if store_message(message_data):
            logger.info("Successfully stored message in database")
        else:
            logger.warning("Failed to store message in database")
        
        await client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to fetch message: {e}")
        return False

async def _test_send_message_async():
    """Test sending a message to Discord."""
    logger.info("Testing message sending...")
    client = get_discord_client()
    
    token = get_discord_token()
    channel_id = get_channel_id()
    
    if not token:
        logger.error("No Discord token available for testing")
        return False
    
    if not channel_id:
        logger.error("No channel ID available for testing")
        return False
    
    try:
        # Login
        await client.login(token)
        await client.connect()
        
        # Get the channel
        channel = client.get_channel(int(channel_id))
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            await client.close()
            return False
        
        # Send a message
        test_message = f"Test message from Discord module test at {datetime.utcnow().isoformat()}"
        await channel.send(test_message)
        logger.info(f"Successfully sent message: {test_message}")
        
        await client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False

def run_simple_test():
    """Run a simple test of the Discord integration."""
    if not validate_discord_env():
        logger.error("Discord environment not properly configured, skipping test")
        return False
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        connection_test = loop.run_until_complete(_test_connection_async())
        if not connection_test:
            logger.error("Connection test failed")
            return False
        
        fetch_test = loop.run_until_complete(_test_fetch_message_async())
        if not fetch_test:
            logger.warning("Fetch message test failed")
        
        # Skip send test for now to avoid spam
        # send_test = loop.run_until_complete(_test_send_message_async())
        # if not send_test:
        #     logger.warning("Send message test failed")
        
        # Test database retrieval
        latest_msg = get_latest_message()
        if latest_msg:
            logger.info(f"Retrieved latest message from database: {latest_msg['content'][:50]}...")
        else:
            logger.warning("Failed to retrieve latest message from database")
        
        msg_count = get_message_count()
        logger.info(f"Total messages in database: {msg_count}")
        
        return True
    except Exception as e:
        logger.error(f"Error during Discord test: {e}")
        return False
    finally:
        loop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_simple_test()
    logger.info(f"Discord test {'succeeded' if success else 'failed'}")