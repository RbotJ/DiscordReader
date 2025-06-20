"""
Discord Bot 
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
from features.discord_bot.services.correlation_service import DiscordCorrelationService
# PostgreSQL event system - imports handled in methods
from features.ingestion.service import IngestionService

logger = logging.getLogger(__name__)

# Global state for singleton pattern
_global_client_manager = None


class TradingDiscordBot(discord.Client):
    """Discord bot for real-time message monitoring and channel management."""

    def __init__(self, ingestion_service=None, channel_manager=None, flask_app=None, *args, **kwargs):
        logger.debug("Instantiating Bot from %s @ %s", TradingDiscordBot.__module__, __file__)
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents, *args, **kwargs)
        self.ready_status = False
        self.aplus_setups_channel_id: Optional[int] = None
        
        # Constructor injection for better testability
        self.ingestion_service = ingestion_service
        self.channel_manager = channel_manager
        self.client_manager = None
        self.flask_app = flask_app  # Store Flask app for context
        
        # Live metrics counters (in-memory, Discord slice only)
        self._messages_today = 0
        self._triggers_today = 0
        self._storage_errors_today = 0
        self._last_storage_error = None
        self._last_reset_date = datetime.utcnow().date()
        self._start_time = datetime.utcnow()

    def _reset_if_needed(self):
        """Reset daily counters at midnight UTC."""
        today = datetime.utcnow().date()
        if today != self._last_reset_date:
            self._messages_today = 0
            self._triggers_today = 0
            self._storage_errors_today = 0
            self._last_storage_error = None
            self._last_reset_date = today
            logger.info(f"Daily metrics counters reset for {today}")

    def _is_trigger_message(self, message):
        """Determine if a message qualifies as a trigger for business logic."""
        content = message.content.lower()
        # Count messages with trading-related content as triggers
        return any(keyword in content for keyword in [
            '@everyone', 'spy', 'nvda', 'tsla', 'qqq', 'aapl', 
            'buy', 'sell', 'breakdown', 'breakout', 'target'
        ])

    async def on_ready(self):
        """Bot startup - scan channels and initialize ingestion."""
        logger.info(f'Discord bot connected as {self.user}')
        self.ready_status = True
        
        # Reset counters if needed on startup
        self._reset_if_needed()
        
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
        
        # Initialize ingestion service with proper client manager wiring
        try:
            # Create a simple client manager that wraps this bot instance
            if not self.client_manager:
                logger.info("Creating client manager wrapper for ingestion service")
                self.client_manager = DiscordClientManager()
                self.client_manager.client = self
                self.client_manager._is_connected = True
                # Set channel_id from bot's configured channel
                self.client_manager.channel_id = str(self.aplus_setups_channel_id) if self.aplus_setups_channel_id else None
            
            # Initialize ingestion service (no constructor parameters needed)
            self.ingestion_service = IngestionService()
            logger.info("Ingestion service initialized with bot client")
            
            # Startup complete - manual sync now available via API
            if self.aplus_setups_channel_id:
                logger.info(f"Bot ready - manual message sync available for channel: {self.aplus_setups_channel_id}")
            else:
                logger.warning("No aplus-setups channel found - manual sync unavailable")
                
        except Exception as e:
            logger.error(f"Error during bot startup ingestion setup: {e}")

    async def _discover_and_sync_channels(self):
        """Use channel manager for discovery and sync operations."""
        try:
            # Use Flask app context for database operations
            if self.flask_app:
                with self.flask_app.app_context():
                    # Sync all channels with database
                    await self.channel_manager.sync_guild_channels(self)
            else:
                logger.warning("No Flask app context available - skipping database sync")
            
            # Discover target channel (no database operations needed)
            target_name = get_channel_name()
            self.aplus_setups_channel_id = await self.channel_manager.discover_target_channel(self, target_name)
            
            if self.aplus_setups_channel_id:
                # Mark channel for listening (uses database - needs context)
                if self.flask_app:
                    with self.flask_app.app_context():
                        self.channel_manager.mark_channel_for_listening(self.aplus_setups_channel_id, True)
                logger.info(f"✅ Target channel configured: {self.aplus_setups_channel_id}")
            else:
                logger.warning("❌ Could not find target channel for ingestion")
                
        except Exception as e:
            logger.error(f"Error during channel discovery and sync: {e}")

    async def on_message(self, message):
        """Handle incoming messages from monitored channels."""
        # Add debug logging as per troubleshooting guide
        print(f"[DEBUG on_message] Author={message.author}, Channel={message.channel.name}, Content={message.content!r}")
        logger.debug(f"Message received: channel.id={message.channel.id!r} ({type(message.channel.id)}), target_channel_id={self.aplus_setups_channel_id!r} ({type(self.aplus_setups_channel_id)})")
        
        # Skip bot's own messages
        if message.author == self.user:
            logger.debug("Skipping bot's own message")
            return
        
        # Reset counters if needed (daily reset)
        self._reset_if_needed()
        
        # Count all messages in target channel (live metrics)
        if str(message.channel.id) == str(self.aplus_setups_channel_id):
            self._messages_today += 1
            
            # Count trigger messages separately
            if self._is_trigger_message(message):
                self._triggers_today += 1
                logger.debug(f"Trigger message detected. Today: {self._messages_today} total, {self._triggers_today} triggers")
            else:
                logger.debug(f"Regular message counted. Today: {self._messages_today} total, {self._triggers_today} triggers")
        
        # Notify status tracker of message activity
        from .status_tracker import get_status_tracker
        tracker = get_status_tracker()
        if tracker:
            await tracker.on_message(message)
            
        # Only process messages from aplus-setups channel (fix type comparison)
        if str(message.channel.id) == str(self.aplus_setups_channel_id):
            logger.info(f"Processing message from #aplus-setups: {message.id}")
            # Update channel activity
            self.channel_manager.update_channel_activity(str(message.channel.id), str(message.id))
            await self._trigger_ingestion(message.channel.id)
        else:
            logger.debug(f"Message from {message.channel.name} (ID={message.channel.id}) doesn't match target channel {self.aplus_setups_channel_id}")

    async def _trigger_ingestion(self, channel_id: int):
        """Trigger ingestion event for new Discord message."""
        try:
            from common.events.publisher import publish_event_async
            await publish_event_async(
                "discord.message.new",
                {"channel_id": str(channel_id)},
                "events",
                "discord_bot"
            )
            logger.info(f"Published PostgreSQL ingestion event for channel: {channel_id}")
        except Exception as e:
            logger.error(f"Error publishing ingestion event: {e}")

    async def _startup_catchup_ingestion(self):
        """Trigger startup catchup ingestion using ingestion service."""
        try:
            if not self.aplus_setups_channel_id:
                logger.warning("No target channel available for startup catchup")
                return
                
            logger.info(f"Starting startup catchup ingestion for channel: {self.aplus_setups_channel_id}")
            
            # Use ingestion service for startup catchup
            result = await self.ingestion_service.ingest_channel_history(
                channel_id=str(self.aplus_setups_channel_id),
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

    async def _manual_sync_history(self, limit: int = 50, before_id: str = None):
        """
        Manually sync message history from the target channel.
        
        Args:
            limit: Number of messages to sync (max 200)
            before_id: Sync messages before this message ID
            
        Returns:
            Dict with sync results and statistics
        """
        try:
            if not self.aplus_setups_channel_id:
                return {
                    'success': False,
                    'error': 'No target channel configured',
                    'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
                }
                
            # Try to get the channel using integer conversion
            try:
                channel_id = int(self.aplus_setups_channel_id)
                channel = self.get_channel(channel_id)
                
                if not channel:
                    # Log available channels for debugging
                    available_channels = [(c.id, c.name) for guild in self.guilds for c in guild.channels if hasattr(c, 'name')]
                    logger.info(f"Available channels: {available_channels}")
                    logger.error(f"Cannot access channel {channel_id}. Bot cache may not include this channel.")
                    return {
                        'success': False,
                        'error': f'Target channel {channel_id} not found in bot cache - permissions may be insufficient',
                        'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
                    }
                    
            except ValueError:
                logger.error(f"Invalid channel ID format: {self.aplus_setups_channel_id}")
                return {
                    'success': False,
                    'error': 'Invalid channel ID format',
                    'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
                }
            
            # Check if bot has permission to read message history
            permissions = channel.permissions_for(channel.guild.me)
            logger.info(f"Bot permissions in channel {channel.name}: read_messages={permissions.read_messages}, read_message_history={permissions.read_message_history}, view_channel={permissions.view_channel}")
            
            if not permissions.read_message_history:
                logger.error(f"Bot lacks read_message_history permission in channel {channel.name}")
                return {
                    'success': False,
                    'error': f'Bot lacks permission to read message history in #{channel.name}. Current permissions: read_messages={permissions.read_messages}, view_channel={permissions.view_channel}',
                    'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
                }
            
            logger.info(f"Starting manual message sync for channel: {self.aplus_setups_channel_id} (limit: {limit})")
            
            # Create ingestion service if not available
            if not self.ingestion_service:
                from features.ingestion.service import IngestionService
                self.ingestion_service = IngestionService()
            
            # Collect messages from Discord using safe async execution
            messages = []
            try:
                logger.info(f"Fetching up to {limit} messages from channel {channel.name} ({channel.id})")
                
                # Define async function to fetch messages
                async def fetch_history():
                    history_messages = []
                    async for msg in channel.history(limit=limit, before=discord.Object(id=before_id) if before_id else None):
                        history_messages.append(msg)
                    return history_messages
                
                # Execute async function safely in bot's event loop
                if hasattr(self, 'loop') and self.loop and self.loop.is_running():
                    # Use bot's existing event loop from different thread
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(fetch_history(), self.loop)
                    history_messages = future.result(timeout=30)  # 30 second timeout
                else:
                    # Fallback: use list comprehension for message collection
                    history_messages = [msg async for msg in channel.history(limit=limit, before=discord.Object(id=before_id) if before_id else None)]
                
                for message in history_messages:
                    messages.append({
                        "id": str(message.id),
                        "content": message.content,
                        "author_id": str(message.author.id),
                        "author_username": message.author.name,
                        "timestamp": message.created_at.isoformat(),
                        "channel_id": str(message.channel.id),
                        "attachments": [{"url": att.url, "filename": att.filename} for att in message.attachments],
                        "embeds": [embed.to_dict() for embed in message.embeds]
                    })
                
                logger.info(f"Successfully fetched {len(messages)} messages from Discord")
                
            except Exception as e:
                logger.error(f"Error fetching message history: {e}")
                return {
                    'success': False,
                    'error': f'Failed to fetch messages: {str(e)}',
                    'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
                }
            
            # Process messages through ingestion
            stored_count = 0
            skipped_count = 0
            error_count = 0
            
            for msg_data in messages:
                try:
                    # Convert to DTO and ingest the message
                    from common.models import DiscordMessageDTO
                    from datetime import datetime
                    
                    message_dto = DiscordMessageDTO(
                        message_id=msg_data["id"],
                        channel_id=msg_data["channel_id"],
                        author_id=msg_data["author_id"],
                        content=msg_data["content"],
                        timestamp=datetime.fromisoformat(msg_data["timestamp"].replace('Z', '+00:00')),
                        guild_id=str(channel.guild.id),
                        author_username=msg_data["author_username"],
                        channel_name=channel.name,
                        attachments=msg_data["attachments"],
                        embeds=msg_data["embeds"]
                    )
                    
                    # Process the message through ingestion service using safe async execution
                    if hasattr(self, 'loop') and self.loop and self.loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            self.ingestion_service.process_message(message_dto), 
                            self.loop
                        )
                        result = future.result(timeout=10)  # 10 second timeout per message
                    else:
                        # Fallback: direct async call (should not happen in manual sync)
                        result = await self.ingestion_service.process_message(message_dto)
                    
                    # Update bot's daily message counter for all processed messages
                    self._messages_today += 1
                    
                    if result:
                        stored_count += 1
                    else:
                        skipped_count += 1
                        # Track storage errors in bot metrics
                        self._storage_errors_today += 1
                        self._last_storage_error = f"Failed to store message {msg_data.get('id')}"
                except Exception as e:
                    logger.error(f"Error ingesting message {msg_data.get('id')}: {e}")
                    error_count += 1
                    # Track storage errors in bot metrics
                    self._storage_errors_today += 1
                    self._last_storage_error = f"Exception processing {msg_data.get('id')}: {str(e)}"
            
            statistics = {
                'total': len(messages),
                'stored': stored_count,
                'skipped': skipped_count,
                'errors': error_count
            }
            
            logger.info(f"Manual sync complete: {statistics}")
            
            return {
                'success': True,
                'statistics': statistics,
                'channel_id': str(self.aplus_setups_channel_id)
            }
            
        except Exception as e:
            logger.error(f"Error during manual message sync: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': {'total': 0, 'stored': 0, 'skipped': 0, 'errors': 1}
            }

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
    
    def get_uptime_seconds(self) -> int:
        """Get bot uptime in seconds."""
        return int((datetime.utcnow() - self._start_time).total_seconds())


class DiscordClientManager:
    """
    Unified Discord client manager with bot integration.
    
    Manages the Discord bot lifecycle and provides access to ingestion services.
    """
    
    def __init__(self, token: Optional[str] = None, channel_id: Optional[str] = None):
        """
        Initialize Discord client manager.
        
        Args:
            token: Discord bot token. If None, will get from standardized environment variable.
            channel_id: Target Discord channel ID for operations.
        """
        self.token = token or get_discord_token()
        self.channel_id = channel_id
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
    
    def get_channel(self, channel_id: int):
        """
        Get a Discord channel by ID through the bot client.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Discord channel object or None if not found
        """
        if not self.client:
            return None
        return self.client.get_channel(channel_id)
    
    async def fetch_channel(self, channel_id: int):
        """
        Fetch a Discord channel by ID through the bot client.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Discord channel object or None if not found
        """
        if not self.client:
            return None
        return await self.client.fetch_channel(channel_id)


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