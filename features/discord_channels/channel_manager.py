"""
Discord Channel Manager

Simplified channel management for moving logic out of bot.py.
Handles channel discovery and metadata without complex typing.
"""

import logging
from typing import Optional
import discord
from common.db import db

logger = logging.getLogger(__name__)


class ChannelManager:
    """Manages Discord channel discovery and database operations."""

    def __init__(self):
        """Initialize the channel manager."""
        pass

    async def discover_target_channel(self, bot_client: discord.Client, target_name: str = "aplus-setups") -> Optional[str]:
        """
        Discover the target channel by name using the bot client.
        
        Args:
            bot_client: Connected Discord bot client
            target_name: Name of channel to find
            
        Returns:
            Optional[str]: Channel ID if found, None otherwise
        """
        if not bot_client.guilds:
            logger.error("Bot is not connected to any Discord guilds")
            return None
            
        # Use the first guild (assumes bot is only in one guild)
        guild = bot_client.guilds[0]
        
        # Find channel by name
        from discord.utils import get
        channel = get(guild.text_channels, name=target_name)
        
        if not channel:
            logger.error(f"Couldn't find a channel called '{target_name}' in {guild.name}")
            logger.info(f"Available channels: {[ch.name for ch in guild.text_channels]}")
            return None
            
        logger.info(f"Found #{channel.name} ({channel.id}) in {guild.name}")
        return str(channel.id)

    async def sync_guild_channels(self, bot_client: discord.Client) -> dict:
        """
        Synchronize all guild channels with database.
        
        Args:
            bot_client: Connected Discord bot client
            
        Returns:
            dict: Statistics about sync operation
        """
        stats = {'channels_found': 0, 'channels_added': 0, 'channels_updated': 0}
        
        try:
            for guild in bot_client.guilds:
                logger.info(f"Syncing channels in guild: {guild.name}")
                
                for channel in guild.text_channels:
                    stats['channels_found'] += 1
                    
                    # Use raw SQL to avoid model typing issues
                    existing = db.session.execute(
                        db.text("SELECT id FROM discord_channels WHERE channel_id = :channel_id"),
                        {'channel_id': str(channel.id)}
                    ).fetchone()
                    
                    if existing:
                        # Update existing channel name if changed
                        db.session.execute(
                            db.text("""
                                UPDATE discord_channels 
                                SET channel_name = :name, guild_name = :guild_name, 
                                    is_active = true, updated_at = NOW()
                                WHERE channel_id = :channel_id
                            """),
                            {
                                'name': channel.name,
                                'guild_name': guild.name,
                                'channel_id': str(channel.id)
                            }
                        )
                        stats['channels_updated'] += 1
                    else:
                        # Insert new channel
                        db.session.execute(
                            db.text("""
                                INSERT INTO discord_channels 
                                (channel_id, channel_name, guild_id, guild_name, channel_type, is_active, created_at)
                                VALUES (:channel_id, :channel_name, :guild_id, :guild_name, 'text', true, NOW())
                            """),
                            {
                                'channel_id': str(channel.id),
                                'channel_name': channel.name,
                                'guild_id': str(guild.id),
                                'guild_name': guild.name
                            }
                        )
                        stats['channels_added'] += 1
                        logger.info(f"Added new channel: #{channel.name} ({channel.id})")
            
            db.session.commit()
            logger.info(f"Channel sync complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during channel sync: {e}")
            db.session.rollback()
            raise

    def get_channel_id_by_name(self, channel_name: str) -> Optional[str]:
        """
        Get channel ID by name from database.
        
        Args:
            channel_name: Name of the channel
            
        Returns:
            Optional[str]: Channel ID if found, None otherwise
        """
        try:
            result = db.session.execute(
                db.text("SELECT channel_id FROM discord_channels WHERE channel_name = :name AND is_active = true"),
                {'name': channel_name}
            ).fetchone()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting channel ID by name: {e}")
            return None

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
            result = db.session.execute(
                db.text("""
                    UPDATE discord_channels 
                    SET is_listen = :listen, updated_at = NOW()
                    WHERE channel_id = :channel_id
                """),
                {'listen': listen, 'channel_id': channel_id}
            )
            
            db.session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Channel {channel_id} listen status set to {listen}")
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
            if message_id:
                db.session.execute(
                    db.text("""
                        UPDATE discord_channels 
                        SET last_seen = NOW(), last_message_id = :message_id, 
                            message_count = COALESCE(message_count, 0) + 1, updated_at = NOW()
                        WHERE channel_id = :channel_id
                    """),
                    {'message_id': message_id, 'channel_id': channel_id}
                )
            else:
                db.session.execute(
                    db.text("""
                        UPDATE discord_channels 
                        SET last_seen = NOW(), updated_at = NOW()
                        WHERE channel_id = :channel_id
                    """),
                    {'channel_id': channel_id}
                )
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating channel activity: {e}")
            db.session.rollback()
            return False