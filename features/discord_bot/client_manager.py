"""
Discord Client Manager Module

Manages Discord client connections and provides a unified interface for 
Discord API operations across the application.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import discord
from datetime import datetime

from .config.settings import validate_discord_token, get_discord_token

logger = logging.getLogger(__name__)


class DiscordClientManager:
    """
    Manages Discord client connections with singleton pattern.
    Provides unified interface for Discord operations.
    """
    
    def __init__(self):
        """Initialize the Discord client manager."""
        self.client: Optional[discord.Client] = None
        self._connected = False
        self._token = None
        
    def is_connected(self) -> bool:
        """
        Check if Discord client is connected.
        
        Returns:
            bool: True if client is connected
        """
        return self._connected and self.client and not self.client.is_closed()
    
    async def connect(self) -> bool:
        """
        Connect to Discord using configured token.
        
        Returns:
            bool: True if connection successful
        """
        try:
            if not validate_discord_token():
                logger.error("Invalid Discord token")
                return False
                
            self._token = get_discord_token()
            
            # Create client with necessary intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            
            self.client = discord.Client(intents=intents)
            
            # Connect asynchronously
            await self.client.login(self._token)
            self._connected = True
            
            logger.info("Discord client connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Discord client: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        try:
            if self.client:
                await self.client.close()
            self._connected = False
            logger.info("Discord client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting Discord client: {e}")
    
    def get_client(self) -> Optional[discord.Client]:
        """
        Get the Discord client instance.
        
        Returns:
            Optional[discord.Client]: Client instance if connected
        """
        return self.client if self.is_connected() else None
    
    async def fetch_channel(self, channel_id: str) -> Optional[discord.TextChannel]:
        """
        Fetch a Discord channel by ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Optional[discord.TextChannel]: Channel if found
        """
        try:
            if not self.is_connected():
                logger.error("Discord client not connected")
                return None
                
            channel = await self.client.fetch_channel(int(channel_id))
            if isinstance(channel, discord.TextChannel):
                return channel
            else:
                logger.warning(f"Channel {channel_id} is not a text channel")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching channel {channel_id}: {e}")
            return None
    
    async def fetch_messages(self, channel_id: str, limit: int = 100) -> list:
        """
        Fetch messages from a Discord channel.
        
        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to fetch
            
        Returns:
            list: List of Discord message objects
        """
        try:
            channel = await self.fetch_channel(channel_id)
            if not channel:
                return []
                
            messages = []
            async for message in channel.history(limit=limit):
                messages.append(message)
                
            logger.debug(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages from channel {channel_id}: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get client status information.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'connected': self.is_connected(),
            'client_ready': self.client is not None and not self.client.is_closed() if self.client else False,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global singleton instance
_client_manager_instance: Optional[DiscordClientManager] = None


def get_client_manager() -> DiscordClientManager:
    """
    Get the global Discord client manager instance.
    
    Returns:
        DiscordClientManager: Singleton client manager
    """
    global _client_manager_instance
    
    if _client_manager_instance is None:
        _client_manager_instance = DiscordClientManager()
    
    return _client_manager_instance


async def ensure_client_connection() -> Optional[DiscordClientManager]:
    """
    Ensure Discord client connection is established.
    
    Returns:
        Optional[DiscordClientManager]: Connected client manager or None
    """
    client_manager = get_client_manager()
    
    if not client_manager.is_connected():
        success = await client_manager.connect()
        if not success:
            return None
    
    return client_manager