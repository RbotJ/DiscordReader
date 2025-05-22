"""
Discord API Client

This module provides a unified interface for interacting with the Discord API.
It handles authentication, rate limiting, and provides methods for common operations.
"""
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
import discord
from discord.ext import tasks

from features.discord.utils.environment import validate_discord_token, get_channel_id

logger = logging.getLogger(__name__)

class DiscordClient:
    """Client for interacting with Discord API."""
    
    def __init__(self):
        """Initialize Discord client."""
        self.client = None
        self.connected = False
        self.ready = False
        
    async def connect(self) -> bool:
        """
        Connect to Discord API.
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if not validate_discord_token():
            logger.error("Cannot connect to Discord: Invalid or missing token")
            return False
            
        try:
            # Create client with appropriate intents
            intents = discord.Intents.default()
            intents.message_content = True
            
            self.client = discord.Client(intents=intents)
            
            # Setup event handlers
            @self.client.event
            async def on_ready():
                logger.info(f"Connected to Discord as {self.client.user}")
                self.ready = True
                
            # Start client
            token = os.environ.get('DISCORD_BOT_TOKEN')
            await self.client.start(token)
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Discord: {e}")
            self.connected = False
            return False
    
    async def fetch_messages(self, channel_type: str = 'default', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch messages from a Discord channel.
        
        Args:
            channel_type: Type of channel to fetch from ('default', 'bot_dialogue', 
                          'setups', or 'test')
            limit: Maximum number of messages to fetch
            
        Returns:
            List of message dictionaries
        """
        if not self.ready or not self.connected:
            logger.error("Cannot fetch messages: Client not ready or connected")
            return []
            
        try:
            channel_id = get_channel_id(channel_type)
            if not channel_id:
                logger.error(f"Cannot fetch messages: Unknown channel type {channel_type}")
                return []
                
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Cannot fetch messages: Channel {channel_id} not found")
                return []
                
            messages = []
            async for message in channel.history(limit=limit):
                messages.append({
                    'message_id': str(message.id),
                    'channel_id': str(message.channel.id),
                    'content': message.content,
                    'author': str(message.author),
                    'created_at': message.created_at.isoformat()
                })
            
            return messages
        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            return []
    
    async def send_message(self, content: str, channel_type: str = 'default') -> Optional[Dict[str, Any]]:
        """
        Send a message to a Discord channel.
        
        Args:
            content: Message content
            channel_type: Type of channel to send to ('default', 'bot_dialogue', 
                          'setups', or 'test')
                          
        Returns:
            Message dictionary or None if failed
        """
        if not self.ready or not self.connected:
            logger.error("Cannot send message: Client not ready or connected")
            return None
            
        try:
            channel_id = get_channel_id(channel_type)
            if not channel_id:
                logger.error(f"Cannot send message: Unknown channel type {channel_type}")
                return None
                
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Cannot send message: Channel {channel_id} not found")
                return None
                
            message = await channel.send(content)
            
            return {
                'message_id': str(message.id),
                'channel_id': str(message.channel.id),
                'content': message.content,
                'author': str(message.author),
                'created_at': message.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

# Singleton instance
_client = None

def get_discord_client() -> DiscordClient:
    """
    Get the Discord client singleton.
    
    Returns:
        DiscordClient instance
    """
    global _client
    if not _client:
        _client = DiscordClient()
    return _client

async def fetch_latest_message(channel_type: str = 'default') -> Optional[Dict[str, Any]]:
    """
    Fetch the latest message from a Discord channel.
    
    Args:
        channel_type: Type of channel to fetch from ('default', 'bot_dialogue', 
                      'setups', or 'test')
                      
    Returns:
        Message dictionary or None if failed
    """
    client = get_discord_client()
    messages = await client.fetch_messages(channel_type, limit=1)
    return messages[0] if messages else None