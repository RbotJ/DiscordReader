"""
Discord Client Module

Provides Discord API client functionality for message ingestion.
This module handles the connection to Discord and basic client operations.
Separated from fetching logic for better separation of concerns.
"""
import asyncio
import logging
import os
from typing import Optional, Dict, Any
import discord
from discord.ext import tasks

logger = logging.getLogger(__name__)

# Global state for singleton pattern
_global_client_manager = None


class TradingDiscordClient(discord.Client):
    """Discord client optimized for trading message fetching."""

    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
        self.channel_id = None
        self.is_ready = False

    async def on_ready(self):
        """Called when the client is ready."""
        logger.info(f'Connected to Discord as {self.user}')
        self.is_ready = True


class DiscordClientManager:
    """
    Manages Discord client instances and connection state.
    
    This class provides a centralized way to manage Discord bot clients
    and handle authentication, reconnection, and client lifecycle.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Discord client manager.
        
        Args:
            token: Discord bot token. If None, will attempt to get from environment.
        """
        self.token = token or os.environ.get('DISCORD_BOT_TOKEN_APLUS')
        self.channel_id = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
        self.client: Optional[TradingDiscordClient] = None
        self._is_connected = False
        self._connection_task = None
    
    async def connect(self) -> bool:
        """
        Establish connection to Discord API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.token:
            logger.error("Discord bot token not provided")
            return False
        
        if not self.channel_id:
            logger.error("Discord channel ID not provided")
            return False
        
        try:
            if self.client and self._is_connected:
                logger.info("Discord client already connected")
                return True
            
            # Create new client instance
            self.client = TradingDiscordClient()
            self.client.channel_id = self.channel_id
            
            # Start client in background task
            self._connection_task = asyncio.create_task(self._run_client())
            
            # Wait for connection to establish
            max_wait = 10  # seconds
            wait_time = 0
            while not self.client.is_ready and wait_time < max_wait:
                await asyncio.sleep(0.5)
                wait_time += 0.5
            
            if self.client.is_ready:
                self._is_connected = True
                logger.info("Discord client connected successfully")
                return True
            else:
                logger.error("Discord client failed to connect within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Discord: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """
        Properly disconnect from Discord API.
        """
        try:
            if self.client:
                await self.client.close()
                self.client = None
            
            if self._connection_task:
                self._connection_task.cancel()
                try:
                    await self._connection_task
                except asyncio.CancelledError:
                    pass
                self._connection_task = None
            
            self._is_connected = False
            logger.info("Discord client disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Discord: {e}")
    
    async def _run_client(self) -> None:
        """
        Run the Discord client.
        """
        try:
            logger.info("Starting Discord client")
            await self.client.start(self.token)
        except Exception as e:
            logger.error(f"Error running Discord client: {e}")
            self._is_connected = False
        finally:
            self._is_connected = False
    
    def get_client(self) -> Optional[TradingDiscordClient]:
        """
        Get the active Discord client instance.
        
        Returns:
            TradingDiscordClient: Active client or None if not connected
        """
        return self.client if self._is_connected else None
    
    def is_connected(self) -> bool:
        """
        Check if client is currently connected to Discord.
        
        Returns:
            bool: Connection status
        """
        return self._is_connected and self.client and self.client.is_ready
    
    def get_channel_id(self) -> Optional[str]:
        """
        Get the configured Discord channel ID.
        
        Returns:
            Optional[str]: Channel ID or None if not configured
        """
        return self.channel_id


def get_discord_client() -> DiscordClientManager:
    """
    Factory function to get a Discord client manager instance.
    Uses singleton pattern to ensure one client per application.
    
    Returns:
        DiscordClientManager: Configured client manager
    """
    global _global_client_manager
    
    if _global_client_manager is None:
        _global_client_manager = DiscordClientManager()
    
    return _global_client_manager


def validate_discord_credentials() -> bool:
    """
    Validate that Discord credentials are properly configured.
    
    Returns:
        bool: True if credentials are valid and accessible
    """
    token = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
    channel_id = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
    
    if not token:
        logger.warning("Discord bot token (DISCORD_BOT_TOKEN_APLUS) not set")
        return False
    
    if not channel_id:
        logger.warning("Discord channel ID (DISCORD_CHANNEL_APLUS_SETUPS) not set")
        return False
    
    try:
        # Validate channel ID is numeric
        int(channel_id)
        return True
    except ValueError:
        logger.error("Discord channel ID must be numeric")
        return False


async def ensure_discord_connection() -> Optional[DiscordClientManager]:
    """
    Ensure Discord connection is established and return client manager.
    
    Returns:
        Optional[DiscordClientManager]: Connected client manager or None if failed
    """
    if not validate_discord_credentials():
        return None
    
    client_manager = get_discord_client()
    
    if not client_manager.is_connected():
        success = await client_manager.connect()
        if not success:
            return None
    
    return client_manager