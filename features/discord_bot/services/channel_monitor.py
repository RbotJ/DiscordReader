"""
Channel Monitor Service

Handles comprehensive Discord channel scanning and database synchronization.
Updates discord_channels table with current server state.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import discord

from features.models.new_schema.discord_channels import DiscordChannel
from common.db import db

logger = logging.getLogger(__name__)


class ChannelMonitor:
    """Service for monitoring and updating Discord channel information."""

    def __init__(self):
        """Initialize channel monitor."""
        self.channels_found = 0
        self.channels_added = 0
        self.channels_updated = 0

    async def scan_and_update_channels(self, bot_client: discord.Client) -> Dict[str, int]:
        """
        Scan all Discord text channels and update database.
        
        Args:
            bot_client: Connected Discord bot client
            
        Returns:
            Dict[str, int]: Statistics about channels processed
        """
        try:
            self.channels_found = 0
            self.channels_added = 0
            self.channels_updated = 0
            
            for guild in bot_client.guilds:
                logger.info(f"Scanning channels in guild: {guild.name}")
                await self._process_guild_channels(guild)
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Channel scan complete: {self.channels_found} found, "
                       f"{self.channels_added} added, {self.channels_updated} updated")
            
            return {
                'channels_found': self.channels_found,
                'channels_added': self.channels_added,
                'channels_updated': self.channels_updated
            }
            
        except Exception as e:
            logger.error(f"Error during channel scan: {e}")
            db.session.rollback()
            raise

    async def _process_guild_channels(self, guild: discord.Guild) -> None:
        """
        Process all text channels in a guild.
        
        Args:
            guild: Discord guild to process
        """
        for channel in guild.text_channels:
            self.channels_found += 1
            await self._update_channel_record(channel, guild)

    async def _update_channel_record(self, channel: discord.TextChannel, guild: discord.Guild) -> None:
        """
        Update or create a channel record in the database.
        
        Args:
            channel: Discord text channel
            guild: Discord guild the channel belongs to
        """
        try:
            # Check if channel exists in database
            existing_channel = DiscordChannel.query.filter_by(
                channel_id=str(channel.id)
            ).first()
            
            if existing_channel:
                # Update existing channel if name changed
                if existing_channel.channel_name != channel.name:
                    logger.info(f"Updating channel name: {existing_channel.channel_name} -> {channel.name}")
                    existing_channel.channel_name = channel.name
                    existing_channel.updated_at = datetime.utcnow()
                    self.channels_updated += 1
                    
                # Ensure channel is marked as active
                if not existing_channel.is_active:
                    existing_channel.is_active = True
                    existing_channel.updated_at = datetime.utcnow()
                    self.channels_updated += 1
                    
            else:
                # Create new channel record
                new_channel = DiscordChannel(
                    channel_id=str(channel.id),
                    channel_name=channel.name,
                    guild_id=str(guild.id),
                    guild_name=guild.name,
                    is_active=True
                )
                db.session.add(new_channel)
                self.channels_added += 1
                logger.info(f"Added new channel: #{channel.name} ({channel.id})")
                
        except Exception as e:
            logger.error(f"Error updating channel {channel.name}: {e}")

    def get_aplus_setups_channel_id(self, bot_client: discord.Client) -> Optional[str]:
        """
        Find the #aplus-setups channel ID from available channels.
        
        Args:
            bot_client: Connected Discord bot client
            
        Returns:
            Optional[str]: Channel ID if found, None otherwise
        """
        for guild in bot_client.guilds:
            for channel in guild.text_channels:
                if channel.name == "aplus-setups":
                    logger.info(f"Found #aplus-setups channel: {channel.id}")
                    return str(channel.id)
        
        logger.warning("Could not find #aplus-setups channel")
        return None

    async def schedule_midnight_update(self, bot_client: discord.Client) -> None:
        """
        Schedule midnight ET channel updates.
        
        Args:
            bot_client: Connected Discord bot client
        """
        # This will be implemented with discord.ext.tasks for recurring updates
        # For now, this is a placeholder for the scheduled functionality
        logger.info("Scheduled midnight channel update (placeholder)")
        pass