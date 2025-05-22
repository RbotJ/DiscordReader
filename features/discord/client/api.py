"""
Discord Client API

This module provides the Discord client API for interacting with Discord.
It handles connecting to Discord, fetching messages, and sending messages.
"""
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

import discord
from discord import TextChannel, Message, Client

from features.discord.utils.environment import get_discord_token, get_channel_id, get_guild_id

logger = logging.getLogger(__name__)

# Singleton Discord client instance
_discord_client = None

class DiscordClient:
    """Discord client wrapper for interacting with Discord API."""
    
    def __init__(self):
        """Initialize the Discord client."""
        self.client = Client(intents=discord.Intents.default())
        self.token = get_discord_token()
        self.connected = False
        
        # Set up event handlers
        @self.client.event
        async def on_ready():
            logger.info(f'Discord client connected as {self.client.user}')
            self.connected = True
            
        @self.client.event
        async def on_message(message):
            # Only log messages from specific channels we care about
            channel_ids = [
                get_channel_id('default'),
                get_channel_id('test'),
                get_channel_id('setups')
            ]
            
            if str(message.channel.id) in channel_ids:
                logger.info(f'Message received: {message.content[:50]}...')
    
    async def connect(self) -> bool:
        """
        Connect to Discord.
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected:
            return True
            
        try:
            if not self.token:
                logger.error("Cannot connect to Discord: Token not found")
                return False
                
            # Start the client in a background task
            asyncio.create_task(self.client.start(self.token))
            
            # Wait for the client to connect
            for _ in range(10):  # Try for 10 seconds
                if self.connected:
                    return True
                await asyncio.sleep(1)
                
            logger.error("Failed to connect to Discord: Timeout")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Discord: {e}")
            return False
            
    async def fetch_messages(self, channel_type: str = 'default', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch messages from a Discord channel.
        
        Args:
            channel_type: Type of channel to fetch from
            limit: Maximum number of messages to fetch
            
        Returns:
            List of message dictionaries
        """
        if not self.connected:
            if not await self.connect():
                return []
                
        channel_id = get_channel_id(channel_type)
        if not channel_id:
            logger.error(f"Channel ID not found for type: {channel_type}")
            return []
            
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel not found with ID: {channel_id}")
                return []
                
            messages = await channel.history(limit=limit).flatten()
            
            # Convert Discord messages to dictionaries
            result = []
            for msg in messages:
                result.append({
                    'id': str(msg.id),
                    'author': msg.author.name,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'channel_id': str(msg.channel.id),
                    'channel_name': msg.channel.name,
                    'attachments': [
                        {'url': attachment.url, 'filename': attachment.filename}
                        for attachment in msg.attachments
                    ]
                })
                
            return result
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
            
    async def send_message(self, content: str, channel_type: str = 'default') -> Optional[Dict[str, Any]]:
        """
        Send a message to a Discord channel.
        
        Args:
            content: Message content
            channel_type: Type of channel to send to
            
        Returns:
            Message dictionary or None if failed
        """
        if not self.connected:
            if not await self.connect():
                return None
                
        channel_id = get_channel_id(channel_type)
        if not channel_id:
            logger.error(f"Channel ID not found for type: {channel_type}")
            return None
            
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel not found with ID: {channel_id}")
                return None
                
            message = await channel.send(content)
            
            # Convert Discord message to dictionary
            result = {
                'id': str(message.id),
                'author': message.author.name,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'channel_id': str(message.channel.id),
                'channel_name': message.channel.name,
                'attachments': [
                    {'url': attachment.url, 'filename': attachment.filename}
                    for attachment in message.attachments
                ]
            }
                
            return result
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
            
    async def disconnect(self):
        """Disconnect from Discord."""
        if self.connected:
            await self.client.close()
            self.connected = False
            logger.info("Discord client disconnected")

def get_discord_client() -> DiscordClient:
    """
    Get the Discord client instance.
    
    Returns:
        DiscordClient: Discord client instance
    """
    global _discord_client
    
    if _discord_client is None:
        _discord_client = DiscordClient()
        
    return _discord_client
    
async def fetch_latest_message(channel_type: str = 'default') -> Optional[Dict[str, Any]]:
    """
    Fetch the latest message from a Discord channel.
    
    Args:
        channel_type: Type of channel to fetch from
        
    Returns:
        Message dictionary or None if not found
    """
    client = get_discord_client()
    messages = await client.fetch_messages(channel_type, limit=1)
    
    if not messages:
        return None
        
    return messages[0]