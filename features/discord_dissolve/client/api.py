"""
Discord Client API

This module provides the Discord client functionality for interacting with Discord.
"""
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timezone

try:
    import discord
    from discord import Client, Intents, Message, TextChannel, DMChannel, GroupChannel
    from discord.abc import GuildChannel, PrivateChannel
    from discord.channel import CategoryChannel, ForumChannel
    from discord.utils import get
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False
    logging.warning("Discord.py package not installed, running in mock mode")

from features.discord.utils.environment import (
    get_discord_token,
    get_channel_id,
    get_guild_id
)

logger = logging.getLogger(__name__)

# Type aliases for clarity
DiscordChannel = Union[TextChannel, DMChannel, GroupChannel, GuildChannel, PrivateChannel, CategoryChannel, ForumChannel]
DiscordClient = Client


class MockDiscordClient:
    """
    Mock Discord client for testing without Discord credentials.
    """
    def __init__(self):
        self.user = type('obj', (object,), {'name': 'MockBot', 'id': '000000000'})
        self.is_ready = True
        
    async def login(self, *args, **kwargs):
        logger.info("Mock Discord client logged in")
        return True
        
    async def start(self, *args, **kwargs):
        logger.info("Mock Discord client started")
        return True
        
    async def close(self):
        logger.info("Mock Discord client closed")
        return True
        
    def get_channel(self, channel_id):
        return MockChannel(channel_id)
        
    def get_guild(self, guild_id):
        return MockGuild(guild_id)


class MockGuild:
    """Mock Discord guild for testing."""
    def __init__(self, guild_id):
        self.id = guild_id
        self.name = "Mock Guild"
        
    def get_channel(self, channel_id):
        return MockChannel(channel_id)


class MockChannel:
    """Mock Discord channel for testing."""
    def __init__(self, channel_id):
        self.id = channel_id
        self.name = "mock-channel"
        
    async def history(self, limit=100, after=None, before=None):
        """Mock message history."""
        messages = [
            MockMessage(
                content=f"Mock message {i}",
                timestamp=datetime.now(timezone.utc),
                channel=self
            )
            for i in range(limit)
        ]
        return MockHistory(messages)
        
    async def send(self, content, **kwargs):
        """Mock sending a message."""
        logger.info(f"Mock message sent to channel {self.id}: {content}")
        return MockMessage(
            content=content,
            timestamp=datetime.now(timezone.utc),
            channel=self
        )


class MockHistory:
    """Mock Discord message history for testing."""
    def __init__(self, messages):
        self.messages = messages
        
    async def flatten(self):
        """Return all messages."""
        return self.messages


class MockMessage:
    """Mock Discord message for testing."""
    def __init__(self, content, timestamp, channel):
        self.content = content
        self.created_at = timestamp
        self.channel = channel
        self.id = "000000000"
        self.author = type('obj', (object,), {'name': 'MockUser', 'id': '000000000'})


def get_discord_client() -> DiscordClient:
    """
    Get a Discord client instance.
    
    Returns:
        Discord client instance or MockDiscordClient if Discord.py not installed
    """
    if not HAS_DISCORD:
        logger.warning("Using mock Discord client")
        return MockDiscordClient()
    
    # Create Discord client with necessary intents
    intents = Intents.default()
    intents.message_content = True
    
    return Client(intents=intents)


async def _fetch_latest_message_async(channel_id: Optional[str] = None, client: Optional[DiscordClient] = None) -> Optional[Dict[str, Any]]:
    """
    Asynchronously fetch the latest message from a Discord channel.
    
    Args:
        channel_id: Discord channel ID to fetch from, or None to use default
        client: Discord client to use, or None to create a new one
        
    Returns:
        Dictionary containing message data or None if not found
    """
    channel_id = channel_id or get_channel_id()
    if not channel_id:
        logger.error("No channel ID provided")
        return None
    
    # Create a new client if one wasn't provided
    client_created = False
    if client is None:
        client = get_discord_client()
        client_created = True
        
        # Login if this is a new client
        token = get_discord_token()
        if not token:
            logger.error("No Discord token available")
            return None
            
        try:
            await client.login(token)
        except Exception as e:
            logger.error(f"Failed to login to Discord: {e}")
            return None
    
    try:
        # Get the channel
        channel = client.get_channel(int(channel_id))
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return None
        
        # Get the latest message
        messages = await channel.history(limit=1).flatten()
        if not messages:
            logger.warning(f"No messages found in channel {channel_id}")
            return None
            
        message = messages[0]
        
        # Format message data
        message_data = {
            'id': str(message.id),
            'content': message.content,
            'author': message.author.name,
            'author_id': str(message.author.id),
            'channel_id': str(message.channel.id),
            'channel_name': getattr(message.channel, 'name', 'direct-message'),
            'timestamp': message.created_at.isoformat(),
            'raw': {
                'id': str(message.id),
                'content': message.content,
                'author': {
                    'name': message.author.name,
                    'id': str(message.author.id)
                },
                'channel': {
                    'id': str(message.channel.id),
                    'name': getattr(message.channel, 'name', 'direct-message')
                },
                'timestamp': message.created_at.isoformat()
            }
        }
        
        return message_data
        
    except Exception as e:
        logger.error(f"Error fetching message: {e}")
        return None
        
    finally:
        # Close the client if we created it
        if client_created:
            await client.close()


def fetch_latest_message(channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest message from a Discord channel.
    
    Args:
        channel_id: Discord channel ID to fetch from, or None to use default
        
    Returns:
        Dictionary containing message data or None if not found
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_fetch_latest_message_async(channel_id))
    finally:
        loop.close()


async def _send_message_async(content: str, channel_id: Optional[str] = None, client: Optional[DiscordClient] = None) -> Optional[Dict[str, Any]]:
    """
    Asynchronously send a message to a Discord channel.
    
    Args:
        content: Message content to send
        channel_id: Discord channel ID to send to, or None to use default
        client: Discord client to use, or None to create a new one
        
    Returns:
        Dictionary containing sent message data or None if failed
    """
    channel_id = channel_id or get_channel_id()
    if not channel_id:
        logger.error("No channel ID provided")
        return None
    
    # Create a new client if one wasn't provided
    client_created = False
    if client is None:
        client = get_discord_client()
        client_created = True
        
        # Login if this is a new client
        token = get_discord_token()
        if not token:
            logger.error("No Discord token available")
            return None
            
        try:
            await client.login(token)
            await client.connect()
        except Exception as e:
            logger.error(f"Failed to login to Discord: {e}")
            return None
    
    try:
        # Get the channel
        channel = client.get_channel(int(channel_id))
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return None
        
        # Send the message
        message = await channel.send(content)
        
        # Format message data
        message_data = {
            'id': str(message.id),
            'content': message.content,
            'author': message.author.name,
            'author_id': str(message.author.id),
            'channel_id': str(message.channel.id),
            'channel_name': getattr(message.channel, 'name', 'direct-message'),
            'timestamp': message.created_at.isoformat()
        }
        
        return message_data
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None
        
    finally:
        # Close the client if we created it
        if client_created:
            await client.close()


def send_message(content: str, channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Send a message to a Discord channel.
    
    Args:
        content: Message content to send
        channel_id: Discord channel ID to send to, or None to use default
        
    Returns:
        Dictionary containing sent message data or None if failed
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_send_message_async(content, channel_id))
    finally:
        loop.close()