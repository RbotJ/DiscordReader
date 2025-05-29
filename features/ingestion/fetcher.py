"""
Message Fetcher Module

Handles the actual fetching of Discord messages using the Discord client.
This module is responsible for retrieving messages from specific channels,
handling pagination, and managing fetch parameters like date ranges and limits.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import discord

# Removed problematic import - DiscordClientManager now injected via dependency injection

logger = logging.getLogger(__name__)


class MessageFetcher:
    """
    Fetches Discord messages from specified channels.
    
    This class handles the logic for retrieving messages with various filters
    and pagination support. It uses the DiscordClientManager for actual API calls.
    """
    
    def __init__(self, client_manager=None):
        """
        Initialize message fetcher with optional client manager.
        
        Args:
            client_manager: Optional client manager (for backward compatibility)
        """
        self.client_manager = client_manager
    
    async def fetch_latest_messages(
        self, 
        channel_id: Optional[str] = None, 
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch the latest messages from a Discord channel.
        
        Args:
            channel_id: Discord channel ID to fetch from (uses default if None)
            limit: Maximum number of messages to fetch
            since: Only fetch messages after this timestamp
            
        Returns:
            List[Dict[str, Any]]: List of message dictionaries
        """
        try:
            # Use configured channel if not specified
            if not channel_id:
                channel_id = self.client_manager.get_channel_id()
            
            if not channel_id:
                logger.error("No channel ID provided or configured")
                return []
            
            # Ensure client is connected
            if not self.client_manager.is_connected():
                logger.warning("Discord client not connected, attempting to connect")
                success = await self.client_manager.connect()
                if not success:
                    logger.error("Failed to connect Discord client")
                    return []
            
            client = self.client_manager.get_client()
            if not client:
                logger.error("No Discord client available")
                return []
            
            # Get the channel
            try:
                channel = client.get_channel(int(channel_id))
                if not channel:
                    channel = await client.fetch_channel(int(channel_id))
            except Exception as e:
                logger.error(f"Error getting channel {channel_id}: {e}")
                return []
            
            # Fetch messages
            messages = []
            async for msg in channel.history(limit=limit, after=since):
                message_data = self._convert_discord_message(msg)
                messages.append(message_data)
            
            logger.info(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def _convert_discord_message(self, message: discord.Message) -> Dict[str, Any]:
        """
        Convert Discord message object to dictionary format.
        
        Args:
            message: Discord message object
            
        Returns:
            Dict[str, Any]: Standardized message dictionary
        """
        try:
            # Handle forwarded messages
            is_forwarded = self._is_forwarded_message(message)
            
            message_data = {
                'id': str(message.id),
                'content': message.content,
                'author': str(message.author),
                'author_id': str(message.author.id),
                'channel_id': str(message.channel.id),
                'timestamp': message.created_at.isoformat(),
                'is_forwarded': is_forwarded,
                'attachments': [
                    {
                        'url': attachment.url,
                        'filename': attachment.filename,
                        'size': attachment.size
                    }
                    for attachment in message.attachments
                ],
                'embeds': [
                    {
                        'title': embed.title,
                        'description': embed.description,
                        'url': embed.url
                    }
                    for embed in message.embeds
                ] if message.embeds else []
            }
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error converting Discord message: {e}")
            return {
                'id': str(message.id),
                'content': message.content or '',
                'author': str(message.author),
                'author_id': str(message.author.id),
                'channel_id': str(message.channel.id),
                'timestamp': message.created_at.isoformat(),
                'is_forwarded': False,
                'attachments': [],
                'embeds': []
            }
    
    def _is_forwarded_message(self, message: discord.Message) -> bool:
        """
        Check if a message appears to be forwarded.
        
        Args:
            message: Discord message to check
            
        Returns:
            bool: True if message appears forwarded
        """
        # Check for common forwarding indicators
        content = message.content.lower()
        forwarding_indicators = [
            'forwarded from',
            'originally from',
            'shared from',
            '> ',  # Quote indicator
        ]
        
        return any(indicator in content for indicator in forwarding_indicators)


async def fetch_latest_messages(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch latest messages with retry logic.
    
    Args:
        limit: Maximum number of messages to fetch
        
    Returns:
        List[Dict[str, Any]]: List of message dictionaries
    """
    retry_attempts = 3
    
    for attempt in range(retry_attempts):
        try:
            # Get client manager and ensure connection
            client_manager = await ensure_discord_connection()
            if not client_manager:
                logger.error(f"Failed to establish Discord connection on attempt {attempt + 1}")
                if attempt == retry_attempts - 1:
                    return []
                await asyncio.sleep(1)
                continue
            
            # Create fetcher and get messages
            fetcher = MessageFetcher(client_manager)
            messages = await fetcher.fetch_latest_messages(limit=limit)
            
            if messages:
                logger.info(f"Successfully fetched {len(messages)} messages on attempt {attempt + 1}")
                return messages
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retry_attempts - 1:
                logger.error("All retry attempts failed")
                return []
            await asyncio.sleep(1)
    
    return []


def get_default_fetch_params() -> Dict[str, Any]:
    """
    Get default parameters for message fetching.
    
    Returns:
        Dict[str, Any]: Default fetch configuration
    """
    return {
        'limit': 50,
        'since_hours': 24,
        'include_embeds': True,
        'include_attachments': True
    }