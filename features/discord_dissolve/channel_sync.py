"""
Discord Channel Sync Module

Discovers and syncs Discord channels to the database for multi-channel management.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError

from common.db import db
from common.models_db import DiscordChannelModel

logger = logging.getLogger(__name__)

async def sync_channels(bot) -> bool:
    """
    Sync Discord channels from all guilds to the database.
    
    Args:
        bot: Discord bot client instance
        
    Returns:
        bool: Success status
    """
    try:
        now = datetime.utcnow()
        synced_count = 0
        
        logger.info("Starting Discord channel sync...")
        
        for guild in bot.guilds:
            logger.info(f"Syncing channels for guild: {guild.name} (ID: {guild.id})")
            
            # Process text channels
            for channel in guild.text_channels:
                try:
                    # Check if channel exists
                    existing = DiscordChannelModel.query.filter_by(
                        guild_id=str(guild.id),
                        channel_id=str(channel.id)
                    ).first()
                    
                    if existing:
                        # Update existing channel
                        existing.name = channel.name
                        existing.channel_type = str(channel.type)
                        existing.last_seen = now
                        existing.is_active = True
                    else:
                        # Create new channel
                        new_channel = DiscordChannelModel(
                            guild_id=str(guild.id),
                            channel_id=str(channel.id),
                            name=channel.name,
                            channel_type=str(channel.type),
                            is_listen=False,
                            is_announce=False,
                            is_active=True,
                            last_seen=now
                        )
                        db.session.add(new_channel)
                    
                    synced_count += 1
                    
                except IntegrityError as e:
                    logger.warning(f"Integrity error syncing channel {channel.name}: {e}")
                    db.session.rollback()
                    continue
                    
        # Commit all changes
        db.session.commit()
        
        # Mark channels not seen as inactive
        cutoff = now
        inactive_channels = DiscordChannelModel.query.filter(
            DiscordChannelModel.last_seen < cutoff,
            DiscordChannelModel.is_active == True
        ).all()
        
        for channel in inactive_channels:
            channel.is_active = False
            
        db.session.commit()
        
        logger.info(f"Channel sync completed. Synced {synced_count} channels, marked {len(inactive_channels)} as inactive")
        return True
        
    except Exception as e:
        logger.error(f"Error during channel sync: {e}")
        db.session.rollback()
        return False

def get_listening_channels() -> List[DiscordChannelModel]:
    """
    Get all channels marked for listening.
    
    Returns:
        List of channels that should be monitored
    """
    return DiscordChannelModel.query.filter_by(
        is_listen=True,
        is_active=True
    ).all()

def get_announce_channels() -> List[DiscordChannelModel]:
    """
    Get all channels marked for announcements.
    
    Returns:
        List of channels that can receive announcements
    """
    return DiscordChannelModel.query.filter_by(
        is_announce=True,
        is_active=True
    ).all()

def set_channel_listen(channel_id: str, is_listen: bool) -> bool:
    """
    Set listen status for a channel.
    
    Args:
        channel_id: Discord channel ID
        is_listen: Whether to listen to this channel
        
    Returns:
        Success status
    """
    try:
        channel = DiscordChannelModel.query.filter_by(channel_id=channel_id).first()
        if channel:
            channel.is_listen = is_listen
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error setting channel listen status: {e}")
        db.session.rollback()
        return False

def set_channel_announce(channel_id: str, is_announce: bool) -> bool:
    """
    Set announce status for a channel.
    
    Args:
        channel_id: Discord channel ID
        is_announce: Whether to announce to this channel
        
    Returns:
        Success status
    """
    try:
        channel = DiscordChannelModel.query.filter_by(channel_id=channel_id).first()
        if channel:
            channel.is_announce = is_announce
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error setting channel announce status: {e}")
        db.session.rollback()
        return False