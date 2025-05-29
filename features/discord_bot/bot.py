"""
Discord Bot - Phase 2 Implementation

Real-time message monitoring with channel scanning and ingestion pipeline integration.
Handles event-driven message processing and channel management.
"""
import asyncio
import logging
import os
from typing import Optional, Dict, Any
import discord
from discord.ext import tasks
from datetime import datetime

from .config.settings import (
    validate_discord_token, 
    get_discord_token, 
    get_channel_name
)
from discord.utils import get
from features.ingestion.service import IngestionService
from features.discord_bot.services.correlation_service import DiscordCorrelationService

logger = logging.getLogger(__name__)

# Global state for singleton pattern
_global_client_manager = None


class TradingDiscordBot(discord.Client):
    """Discord bot for real-time message monitoring and channel management."""

    def __init__(self, *args, **kwargs):
        import os
        print(f"🤖 Instantiating Bot from {TradingDiscordBot.__module__!r} @ {os.path.abspath(__file__)}")
        logging.getLogger().info(f"🤖 Instantiating Bot from {TradingDiscordBot.__module__!r} @ {os.path.abspath(__file__)}")
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents, *args, **kwargs)
        self.ready_status = False
        self.aplus_setups_channel_id = None
        self.ingestion_service = IngestionService()
        self.client_manager = None

    async def on_ready(self):
        """Bot startup - scan channels and initialize ingestion."""
        logger.info(f'Discord bot connected as {self.user}')
        self.ready_status = True
        
        # Dynamic channel discovery
        await self._discover_target_channel()
        
        # Initialize channel monitoring service
        await self._scan_and_update_channels()
        
        # Log startup status for debugging
        logger.info(f"Bot startup status - client_manager: {self.client_manager is not None}, aplus_channel: {self.aplus_setups_channel_id}")
        
        # Initialize ingestion service (don't require client_manager for basic functionality)
        try:
            if not self.client_manager:
                logger.warning("No client_manager available, initializing ingestion service without it")
                self.ingestion_service = IngestionService()
            else:
                self.ingestion_service = IngestionService(discord_client_manager=self.client_manager)
                logger.info("Ingestion service initialized with bot client")
            
            # Trigger startup catch-up ingestion if target channel found
            if self.aplus_setups_channel_id:
                logger.info(f"Triggering startup catchup ingestion for channel: {self.aplus_setups_channel_id}")
                await self._startup_catchup_ingestion()
            else:
                logger.warning("No aplus-setups channel found, skipping catchup ingestion")
                
        except Exception as e:
            logger.error(f"Error during bot startup ingestion setup: {e}")

    async def _discover_target_channel(self):
        """Discover the target channel by name using dynamic discovery."""
        if not self.guilds:
            logger.error("❌ Bot is not connected to any Discord guilds")
            return
            
        # Use the first guild (assumes bot is only in one guild)
        guild = self.guilds[0]
        target_name = get_channel_name()
        
        # Find channel by name
        channel = get(guild.text_channels, name=target_name)
        
        if not channel:
            logger.error(f"❌ Couldn't find a channel called '{target_name}' in {guild.name}")
            logger.info(f"Available channels: {[ch.name for ch in guild.text_channels]}")
            return
            
        # Store the discovered channel ID
        self.aplus_setups_channel_id = str(channel.id)
        logger.info(f"✅ Monitoring #{channel.name} ({channel.id}) in {guild.name}")

    async def on_message(self, message):
        """Handle incoming messages from monitored channels."""
        # Skip bot's own messages
        if message.author == self.user:
            return
            
        # Only process messages from aplus-setups channel
        if str(message.channel.id) == self.aplus_setups_channel_id:
            logger.info(f"Processing message from #aplus-setups: {message.id}")
            await self._trigger_ingestion(message.channel.id)

    async def _scan_and_update_channels(self):
        """Scan all text channels and update database."""
        from features.discord_bot.services.channel_monitor import ChannelMonitor
        
        try:
            monitor = ChannelMonitor()
            channels_updated = await monitor.scan_and_update_channels(self)
            
            # Find aplus-setups channel
            for guild in self.guilds:
                for channel in guild.text_channels:
                    if channel.name == "aplus-setups":
                        self.aplus_setups_channel_id = str(channel.id)
                        logger.info(f"Found #aplus-setups channel: {self.aplus_setups_channel_id}")
                        break
                        
            if not self.aplus_setups_channel_id:
                logger.warning("Could not find #aplus-setups channel for ingestion")
                
        except Exception as e:
            logger.error(f"Error scanning channels: {e}")

    async def _startup_catchup_ingestion(self):
        """Trigger catch-up ingestion on startup using last message in database with correlation tracking."""
        correlation_id = DiscordCorrelationService.generate_message_correlation_id()
        
        try:
            from features.ingestion.models import DiscordMessageModel
            
            # Get timestamp of last message in database for aplus-setups channel
            last_message = DiscordMessageModel.query.filter_by(
                channel_id=self.aplus_setups_channel_id
            ).order_by(DiscordMessageModel.timestamp.desc()).first()
            
            since_timestamp = last_message.timestamp if last_message else None
            
            if since_timestamp:
                logger.info(f"Starting catch-up ingestion since last message: {since_timestamp}")
            else:
                logger.info("No previous messages found, starting full ingestion")
            
            # Publish ingestion started event with correlation tracking
            DiscordCorrelationService.publish_ingestion_started({
                'channel_id': self.aplus_setups_channel_id,
                'ingestion_type': 'startup_catchup',
                'since_timestamp': since_timestamp.isoformat() if since_timestamp else None,
                'limit': 200
            }, correlation_id)
            
            # Trigger catch-up ingestion with larger limit for startup
            result = await self.ingestion_service.ingest_latest_messages(
                channel_id=self.aplus_setups_channel_id,
                limit=200,  # Larger limit for catch-up
                since=since_timestamp
            )
            
            # Publish ingestion completed event with results
            DiscordCorrelationService.publish_ingestion_completed({
                **result.get('statistics', {}),
                'channel_id': self.aplus_setups_channel_id,
                'ingestion_type': 'startup_catchup'
            }, correlation_id)
            
            logger.info(f"Startup catch-up ingestion completed: {result.get('statistics', {})}")
            
        except Exception as e:
            logger.error(f"Error during startup catch-up ingestion: {e}")
            # Publish error event
            DiscordCorrelationService.publish_ingestion_completed({
                'error': str(e),
                'channel_id': self.aplus_setups_channel_id,
                'ingestion_type': 'startup_catchup',
                'success': False
            }, correlation_id)

    async def _trigger_ingestion(self, channel_id: str):
        """Trigger message ingestion for a specific channel with correlation tracking."""
        correlation_id = DiscordCorrelationService.generate_message_correlation_id()
        
        if not self.ingestion_service:
            logger.error("Ingestion service not initialized")
            return
            
        try:
            # Publish ingestion started event
            DiscordCorrelationService.publish_ingestion_started({
                'channel_id': channel_id,
                'ingestion_type': 'real_time_trigger',
                'limit': 50
            }, correlation_id)
            
            # Ingest latest 50 messages since last trigger
            result = await self.ingestion_service.ingest_latest_messages(
                channel_id=channel_id,
                limit=50,
                since=self.ingestion_service.get_last_triggered()
            )
            
            # Publish ingestion completed event with results
            DiscordCorrelationService.publish_ingestion_completed({
                **result.get('statistics', {}),
                'channel_id': channel_id,
                'ingestion_type': 'real_time_trigger'
            }, correlation_id)
            
            logger.info(f"Ingestion completed: {result.get('statistics', {})}")
            
        except Exception as e:
            logger.error(f"Error triggering ingestion: {e}")
            # Publish error event
            DiscordCorrelationService.publish_ingestion_completed({
                'error': str(e),
                'channel_id': channel_id,
                'ingestion_type': 'real_time_trigger',
                'success': False
            }, correlation_id)

    def is_ready(self) -> bool:
        """Check if bot is ready."""
        return self.ready_status


class DiscordClientManager:
    """
    Unified Discord client manager with bot integration.
    
    Manages the Discord bot lifecycle and provides access to ingestion services.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Discord client manager.
        
        Args:
            token: Discord bot token. If None, will get from standardized environment variable.
        """
        self.token = token or get_discord_token()
        self.client: Optional[TradingDiscordBot] = None
        self._is_connected = False
        self._connection_task = None
    
    async def connect(self) -> bool:
        """
        Establish connection to Discord API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.token:
            logger.error("Discord bot token not provided - check DISCORD_BOT_TOKEN environment variable")
            return False
        
        try:
            if self.client and self._is_connected:
                logger.info("Discord client already connected")
                return True
            
            # Create new bot instance
            self.client = TradingDiscordBot()
            self.client.client_manager = self  # Inject client manager reference
            
            # Start client in background task
            self._connection_task = asyncio.create_task(self._run_client())
            
            # Wait for connection to establish
            max_wait = 10  # seconds
            wait_time = 0
            while not self.client.is_ready() and wait_time < max_wait:
                await asyncio.sleep(0.5)
                wait_time += 0.5
            
            if self.client.is_ready():
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
            logger.info("Starting Discord client with standardized token")
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
        return self._is_connected and self.client and self.client.is_ready()
    
    def get_channel_id(self) -> Optional[str]:
        """
        Get the configured Discord channel ID.
        
        Returns:
            Optional[str]: Channel ID or None if not configured
        """
        return self.channel_id


def get_discord_client() -> DiscordClientManager:
    """
    Factory function to get a unified Discord client manager instance.
    Uses singleton pattern to ensure one client per application.
    
    Returns:
        DiscordClientManager: Configured client manager with standardized environment variables
    """
    global _global_client_manager
    
    if _global_client_manager is None:
        _global_client_manager = DiscordClientManager()
    
    return _global_client_manager


def validate_discord_credentials() -> bool:
    """
    Validate that Discord credentials are properly configured using standardized variables.
    
    Returns:
        bool: True if credentials are valid and accessible
    """
    return validate_discord_token()


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