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
from features.ingestion.service import IngestionService
from features.discord_bot.services.correlation_service import DiscordCorrelationService
from features.discord_channels.channel_manager import ChannelManager

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
        self.channel_manager = ChannelManager()

    async def on_ready(self):
        """Bot startup - scan channels and initialize ingestion."""
        logger.info(f'Discord bot connected as {self.user}')
        self.ready_status = True
        
        # Initialize status tracker and notify it of ready event
        from .status_tracker import initialize_status_tracker, get_status_tracker
        initialize_status_tracker(self)
        tracker = get_status_tracker()
        if tracker:
            await tracker.on_ready()
        
        # Use channel manager for discovery and sync
        await self._discover_and_sync_channels()
        
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

    async def _discover_and_sync_channels(self):
        """Use channel manager for discovery and sync operations."""
        try:
            # Sync all channels with database
            await self.channel_manager.sync_guild_channels(self)
            
            # Discover target channel
            target_name = get_channel_name()
            self.aplus_setups_channel_id = await self.channel_manager.discover_target_channel(self, target_name)
            
            if self.aplus_setups_channel_id:
                # Mark channel for listening
                self.channel_manager.mark_channel_for_listening(self.aplus_setups_channel_id, True)
                logger.info(f"✅ Target channel configured: {self.aplus_setups_channel_id}")
            else:
                logger.warning("❌ Could not find target channel for ingestion")
                
        except Exception as e:
            logger.error(f"Error during channel discovery and sync: {e}")

    async def on_message(self, message):
        """Handle incoming messages from monitored channels."""
        # Skip bot's own messages
        if message.author == self.user:
            return
            
        # Only process messages from aplus-setups channel
        if str(message.channel.id) == self.aplus_setups_channel_id:
            logger.info(f"Processing message from #aplus-setups: {message.id}")
            # Update channel activity
            self.channel_manager.update_channel_activity(str(message.channel.id), str(message.id))
            await self._trigger_ingestion(message.channel.id)



    async def _startup_catchup_ingestion(self):
        """Trigger startup catchup ingestion using ingestion service."""
        try:
            if not self.aplus_setups_channel_id:
                logger.warning("No target channel available for startup catchup")
                return
                
            logger.info(f"Starting startup catchup ingestion for channel: {self.aplus_setups_channel_id}")
            
            # Use ingestion service for startup catchup
            result = await self.ingestion_service.ingest_channel_history(
                channel_id=self.aplus_setups_channel_id,
                limit=50,
                source="startup_catchup"
            )
            
            if result and result.get('success'):
                stats = result.get('statistics', {})
                logger.info(f"Startup ingestion complete: {stats}")
            else:
                logger.warning(f"Startup ingestion had issues: {result}")
                
        except Exception as e:
            logger.error(f"Error during startup catchup ingestion: {e}")

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
    
    def get_client(self) -> Optional[TradingDiscordBot]:
        """
        Get the active Discord client instance.
        
        Returns:
            TradingDiscordBot: Active client or None if not connected
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