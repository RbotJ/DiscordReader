"""
Discord Channels Service

Service layer for managing Discord channel discovery, metadata, and persistent storage.
Provides clean interface for channel operations without direct database access.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import discord

from .models import DiscordChannel
from common.db import db

logger = logging.getLogger(__name__)


class DiscordChannelService:
    """Service for Discord channel management and metadata operations."""

    def __init__(self):
        """Initialize the Discord channel service."""
        self.stats = {
            'channels_found': 0,
            'channels_added': 0,
            'channels_updated': 0
        }

    async def discover_and_sync_channels(self, bot_client: discord.Client) -> Dict[str, int]:
        """
        Discover all Discord channels and synchronize with database.
        
        Args:
            bot_client: Connected Discord bot client
            
        Returns:
            Dict[str, int]: Statistics about channels processed
        """
        try:
            self._reset_stats()
            
            for guild in bot_client.guilds:
                logger.info(f"Scanning channels in guild: {guild.name}")
                await self._sync_guild_channels(guild)
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Channel sync complete: {self.stats['channels_found']} found, "
                       f"{self.stats['channels_added']} added, {self.stats['channels_updated']} updated")
            
            return self.stats.copy()
            
        except Exception as e:
            logger.error(f"Error during channel discovery: {e}")
            db.session.rollback()
            raise

    async def _sync_guild_channels(self, guild: discord.Guild) -> None:
        """
        Synchronize all text channels in a guild with database.
        
        Args:
            guild: Discord guild to process
        """
        for channel in guild.text_channels:
            self.stats['channels_found'] += 1
            await self._sync_channel_record(channel, guild)

    async def _sync_channel_record(self, channel: discord.TextChannel, guild: discord.Guild) -> None:
        """
        Synchronize a single channel record with database.
        
        Args:
            channel: Discord text channel
            guild: Discord guild the channel belongs to
        """
        try:
            existing_channel = DiscordChannel.find_by_channel_id(str(channel.id))
            
            if existing_channel:
                # Update existing channel
                updated = False
                
                if existing_channel.channel_name != channel.name:
                    logger.info(f"Updating channel name: {existing_channel.channel_name} -> {channel.name}")
                    existing_channel.channel_name = channel.name
                    updated = True
                    
                if existing_channel.guild_name != guild.name:
                    existing_channel.guild_name = guild.name
                    updated = True
                    
                if not existing_channel.is_active:
                    existing_channel.is_active = True
                    updated = True
                
                if updated:
                    existing_channel.updated_at = datetime.utcnow()
                    self.stats['channels_updated'] += 1
                    
            else:
                # Create new channel record
                new_channel = DiscordChannel(
                    channel_id=str(channel.id),
                    channel_name=channel.name,
                    guild_id=str(guild.id),
                    guild_name=guild.name,
                    channel_type="text",
                    is_active=True
                )
                db.session.add(new_channel)
                self.stats['channels_added'] += 1
                logger.info(f"Added new channel: #{channel.name} ({channel.id})")
                
        except Exception as e:
            logger.error(f"Error syncing channel {channel.name}: {e}")

    def find_channel_by_name(self, channel_name: str) -> Optional[DiscordChannel]:
        """
        Find a channel by name.
        
        Args:
            channel_name: Name of the channel to find
            
        Returns:
            Optional[DiscordChannel]: Channel if found, None otherwise
        """
        return DiscordChannel.find_by_name(channel_name)

    def find_channel_by_id(self, channel_id: str) -> Optional[DiscordChannel]:
        """
        Find a channel by Discord ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Optional[DiscordChannel]: Channel if found, None otherwise
        """
        return DiscordChannel.find_by_channel_id(channel_id)

    def get_target_channel_id(self, target_name: str = "aplus-setups") -> Optional[str]:
        """
        Get the channel ID for a target channel name.
        
        Args:
            target_name: Name of the target channel
            
        Returns:
            Optional[str]: Channel ID if found, None otherwise
        """
        channel = self.find_channel_by_name(target_name)
        return channel.channel_id if channel else None

    def mark_channel_for_listening(self, channel_id: str, listen: bool = True) -> bool:
        """
        Mark a channel for message listening.
        
        Args:
            channel_id: Discord channel ID
            listen: Whether to listen to this channel
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            channel = DiscordChannel.find_by_channel_id(channel_id)
            if channel:
                channel.is_listen = listen
                channel.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Channel {channel.channel_name} listen status set to {listen}")
                return True
            else:
                logger.warning(f"Channel with ID {channel_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error updating channel listen status: {e}")
            db.session.rollback()
            return False

    def update_channel_activity(self, channel_id: str, message_id: str = None) -> bool:
        """
        Update channel activity metadata.
        
        Args:
            channel_id: Discord channel ID
            message_id: Optional message ID for tracking
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            channel = DiscordChannel.find_by_channel_id(channel_id)
            if channel:
                channel.update_last_seen(message_id)
                if message_id:
                    channel.message_count += 1
                db.session.commit()
                return True
            else:
                logger.warning(f"Channel with ID {channel_id} not found for activity update")
                return False
        except Exception as e:
            logger.error(f"Error updating channel activity: {e}")
            db.session.rollback()
            return False

    def get_listening_channels(self) -> List[DiscordChannel]:
        """
        Get all channels marked for listening.
        
        Returns:
            List[DiscordChannel]: List of channels to listen to
        """
        return DiscordChannel.find_listening_channels()

    def get_active_channels(self) -> List[DiscordChannel]:
        """
        Get all active channels.
        
        Returns:
            List[DiscordChannel]: List of active channels
        """
        return DiscordChannel.find_active_channels()

    def _reset_stats(self) -> None:
        """Reset operation statistics."""
        self.stats = {
            'channels_found': 0,
            'channels_added': 0,
            'channels_updated': 0
        }