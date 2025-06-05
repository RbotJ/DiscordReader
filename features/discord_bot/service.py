"""
Discord Bot Service Layer

Centralized service for Discord bot operations, providing a clean interface
for message handling, channel management, and bot lifecycle without exposing
implementation details to the bot controller.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from common.events.bus import get_event_bus, publish_cross_slice_event
from common.models import DiscordMessageDTO

logger = logging.getLogger(__name__)


@dataclass
class BotStatus:
    """Bot status information."""
    is_connected: bool
    guild_count: int
    user_count: int
    latency: float
    uptime: Optional[datetime] = None


@dataclass
class ChannelInfo:
    """Channel information."""
    channel_id: str
    name: str
    guild_id: str
    guild_name: str
    member_count: int
    is_monitored: bool


class BotService:
    """Service for Discord bot operations."""
    
    def __init__(self):
        self._bot_instance = None
        self._monitored_channels = set()
        self._startup_complete = False
        
    def set_bot_instance(self, bot):
        """Set the Discord bot instance."""
        self._bot_instance = bot
        
    async def handle_message_received(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle a new Discord message.
        
        Args:
            message_data: Raw message data from Discord
            
        Returns:
            True if message was processed successfully
        """
        try:
            # Convert to standardized DTO
            message_dto = DiscordMessageDTO(
                message_id=str(message_data.get('id', '')),
                channel_id=str(message_data.get('channel', {}).get('id', '')),
                author_id=str(message_data.get('author', {}).get('id', '')),
                content=message_data.get('content', ''),
                timestamp=datetime.fromisoformat(message_data.get('timestamp', datetime.now().isoformat())),
                guild_id=str(message_data.get('guild', {}).get('id', '')) if message_data.get('guild') else None,
                author_username=message_data.get('author', {}).get('username', ''),
                channel_name=message_data.get('channel', {}).get('name', ''),
                attachments=message_data.get('attachments', []),
                embeds=message_data.get('embeds', [])
            )
            
            # Publish message event for other slices to handle
            await publish_cross_slice_event(
                "discord.message_received",
                {
                    "message": {
                        "message_id": message_dto.message_id,
                        "channel_id": message_dto.channel_id,
                        "author_id": message_dto.author_id,
                        "content": message_dto.content,
                        "timestamp": message_dto.timestamp.isoformat(),
                        "guild_id": message_dto.guild_id,
                        "author_username": message_dto.author_username,
                        "channel_name": message_dto.channel_name,
                        "attachments": message_dto.attachments,
                        "embeds": message_dto.embeds
                    }
                },
                "discord_bot"
            )
            
            logger.debug(f"Published message event for message {message_dto.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return False
            
    async def get_bot_status(self) -> Optional[BotStatus]:
        """
        Get current bot status.
        
        Returns:
            BotStatus or None if bot not available
        """
        if not self._bot_instance:
            return None
            
        try:
            return BotStatus(
                is_connected=self._bot_instance.is_ready(),
                guild_count=len(self._bot_instance.guilds),
                user_count=sum(guild.member_count for guild in self._bot_instance.guilds),
                latency=self._bot_instance.latency
            )
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return None
            
    async def get_monitored_channels(self) -> List[ChannelInfo]:
        """
        Get list of monitored channels.
        
        Returns:
            List of ChannelInfo objects
        """
        channels = []
        
        if not self._bot_instance:
            return channels
            
        try:
            for channel_id in self._monitored_channels:
                channel = self._bot_instance.get_channel(int(channel_id))
                if channel:
                    channels.append(ChannelInfo(
                        channel_id=str(channel.id),
                        name=channel.name,
                        guild_id=str(channel.guild.id),
                        guild_name=channel.guild.name,
                        member_count=channel.guild.member_count,
                        is_monitored=True
                    ))
                    
        except Exception as e:
            logger.error(f"Error getting monitored channels: {e}")
            
        return channels
        
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get Discord bot service metrics.
        
        Returns:
            Dict containing bot metrics
        """
        return {
            'bot_connected': self._bot_instance is not None and getattr(self._bot_instance, 'is_ready', lambda: False)(),
            'monitored_channels': len(self._monitored_channels),
            'startup_complete': self._startup_complete,
            'guild_count': len(self._bot_instance.guilds) if self._bot_instance else 0,
            'latency': getattr(self._bot_instance, 'latency', 0.0),
            'service_type': 'discord_bot'
        }
        
    async def add_monitored_channel(self, channel_id: str) -> bool:
        """
        Add a channel to monitoring.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if channel was added successfully
        """
        try:
            self._monitored_channels.add(channel_id)
            
            # Publish channel monitoring event
            await publish_cross_slice_event(
                "discord.channel_monitoring_added",
                {"channel_id": channel_id},
                "discord_bot"
            )
            
            logger.info(f"Added channel {channel_id} to monitoring")
            return True
            
        except Exception as e:
            logger.error(f"Error adding monitored channel {channel_id}: {e}")
            return False
            
    async def remove_monitored_channel(self, channel_id: str) -> bool:
        """
        Remove a channel from monitoring.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if channel was removed successfully
        """
        try:
            self._monitored_channels.discard(channel_id)
            
            # Publish channel monitoring event
            await publish_cross_slice_event(
                "discord.channel_monitoring_removed",
                {"channel_id": channel_id},
                "discord_bot"
            )
            
            logger.info(f"Removed channel {channel_id} from monitoring")
            return True
            
        except Exception as e:
            logger.error(f"Error removing monitored channel {channel_id}: {e}")
            return False
            
    async def send_message(self, channel_id: str, content: str) -> bool:
        """
        Send a message to a Discord channel.
        
        Args:
            channel_id: Discord channel ID
            content: Message content
            
        Returns:
            True if message was sent successfully
        """
        if not self._bot_instance:
            logger.error("Bot instance not available")
            return False
            
        try:
            channel = self._bot_instance.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return False
                
            await channel.send(content)
            logger.info(f"Sent message to channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to channel {channel_id}: {e}")
            return False
            
    async def perform_startup_ingestion(self) -> Dict[str, Any]:
        """
        Request startup message ingestion from the ingestion service.
        
        Returns:
            Ingestion results
        """
        try:
            # Request ingestion through event bus
            bus = await get_event_bus()
            
            response = await bus.request_response(
                "ingestion.startup_request",
                {"trigger": "bot_startup"},
                "discord_bot",
                "ingestion.startup_response",
                timeout=30.0
            )
            
            if response:
                self._startup_complete = True
                logger.info(f"Startup ingestion complete: {response}")
                return response
            else:
                logger.warning("Startup ingestion request timed out")
                return {"status": "timeout"}
                
        except Exception as e:
            logger.error(f"Error during startup ingestion: {e}")
            return {"status": "error", "message": str(e)}
            
    def is_startup_complete(self) -> bool:
        """Check if startup ingestion is complete."""
        return self._startup_complete
        
    async def get_channel_history(self, channel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent message history from a channel.
        
        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message data
        """
        if not self._bot_instance:
            return []
            
        try:
            channel = self._bot_instance.get_channel(int(channel_id))
            if not channel:
                return []
                
            messages = []
            async for message in channel.history(limit=limit):
                messages.append({
                    "id": str(message.id),
                    "content": message.content,
                    "author_id": str(message.author.id),
                    "author_username": message.author.name,
                    "timestamp": message.created_at.isoformat(),
                    "attachments": [{"url": att.url, "filename": att.filename} for att in message.attachments],
                    "embeds": [embed.to_dict() for embed in message.embeds]
                })
                
            return messages
            
        except Exception as e:
            logger.error(f"Error getting channel history for {channel_id}: {e}")
            return []


# Global service instance
_discord_bot_service = None


def get_discord_bot_service() -> BotService:
    """Get the Discord bot service instance."""
    global _discord_bot_service
    if _discord_bot_service is None:
        _discord_bot_service = BotService()
    return _discord_bot_service