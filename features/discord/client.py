"""
Discord Client Module

This module provides functionality to connect to Discord and fetch messages
from the trading setups channel using discord.py.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

import discord
from discord.ext import tasks

from features.discord.message_parser import parse_message
from common.events import EventChannels, publish_event
from common.db import db

# Configure logger
logger = logging.getLogger(__name__)

# Global state
_client = None
_channel = None
_is_connected = False
_last_message_time = None
_message_handlers = []

class TradingDiscordClient(discord.Client):
    """Discord client for fetching trading setup messages."""

    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
        self.channel_id = None
        self.last_message_id = None
        self.is_ready = False

    async def on_ready(self):
        """Called when the client is ready."""
        logger.info(f'Connected to Discord as {self.user}')
        self.is_ready = True

        # Start background task to check for new messages
        self.check_for_messages.start()

    @tasks.loop(minutes=1)
    async def check_for_messages(self):
        """Check for new messages periodically."""
        try:
            if not self.channel_id:
                logger.warning("Channel ID not set, cannot check for messages")
                return

            channel = self.get_channel(int(self.channel_id))
            if not channel:
                logger.warning(f"Could not find channel with ID {self.channel_id}")
                return

            # Fetch recent messages
            messages = []
            async for message in channel.history(limit=10):
                messages.append(message)

            if not messages:
                logger.info("No recent messages found")
                return

            # Process newest messages first
            messages.reverse()

            for message in messages:
                # Skip if we've already seen this message
                if self.last_message_id and message.id <= self.last_message_id:
                    continue

                # Update last message ID
                self.last_message_id = message.id

                # Process message
                logger.info(f"New message from {message.author}: {message.content[:50]}...")

                # Parse the message
                parsed_data = parse_message(message.content)

                # Add message metadata
                parsed_data['message_id'] = str(message.id)
                parsed_data['author'] = str(message.author)
                parsed_data['timestamp'] = message.created_at.isoformat()

                # Call message handlers
                for handler in _message_handlers:
                    try:
                        handler(parsed_data)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")

        except Exception as e:
            logger.error(f"Error checking for messages: {e}")

    @check_for_messages.before_loop
    async def before_check_for_messages(self):
        """Wait until the bot is ready before starting the task."""
        await self.wait_until_ready()

def is_discord_available() -> bool:
    """
    Check if Discord connection is available.

    Returns:
        True if Discord token is configured and client is connected
    """
    token = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
    channel_id = os.environ.get('DISCORD_CHANNEL_ID')

    if not token or not channel_id:
        logger.warning("Discord token (DISCORD_BOT_TOKEN_APLUS) or channel ID not set")
        return False

    return _is_connected

def init_discord_client() -> bool:
    """
    Initialize Discord client.

    Returns:
        Success status
    """
    global _client, _is_connected

    try:
        # Check for Discord token
        token = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
        channel_id = os.environ.get('DISCORD_CHANNEL_ID')

        if not token or not channel_id:
            logger.warning("Discord token (DISCORD_BOT_TOKEN_APLUS) or channel ID not set")
            return False

        # Create client if not already created
        if not _client:
            _client = TradingDiscordClient()
            _client.channel_id = channel_id

            # Start the client in a background task
            asyncio.create_task(_run_discord_client(token))

            # Wait a bit for connection
            asyncio.sleep(2)

        return True

    except Exception as e:
        logger.error(f"Error initializing Discord client: {e}")
        return False

async def _run_discord_client(token: str) -> None:
    """
    Run the Discord client.

    Args:
        token: Discord bot token
    """
    global _is_connected

    try:
        logger.info("Starting Discord client")
        _is_connected = True
        await _client.start(token)
    except Exception as e:
        logger.error(f"Error running Discord client: {e}")
        _is_connected = False
    finally:
        _is_connected = False

def shutdown_discord_client() -> bool:
    """
    Shutdown Discord client.

    Returns:
        Success status
    """
    global _client, _is_connected

    try:
        if _client:
            asyncio.create_task(_client.close())
            _client = None
            _is_connected = False
        return True
    except Exception as e:
        logger.error(f"Error shutting down Discord client: {e}")
        return False

def register_message_handler(handler_func) -> bool:
    """
    Register a function to be called when a new message is received.

    Args:
        handler_func: Function that takes a parsed message dict as input

    Returns:
        Success status
    """
    global _message_handlers

    try:
        _message_handlers.append(handler_func)
        return True
    except Exception as e:
        logger.error(f"Error registering message handler: {e}")
        return False

def unregister_message_handler(handler_func) -> bool:
    """
    Unregister a message handler.

    Args:
        handler_func: Function to unregister

    Returns:
        Success status
    """
    global _message_handlers

    try:
        if handler_func in _message_handlers:
            _message_handlers.remove(handler_func)
        return True
    except Exception as e:
        logger.error(f"Error unregistering message handler: {e}")
        return False

async def fetch_recent_messages(limit: int = 10) -> List[Dict]:
    """
    Fetch recent messages from the Discord channel.

    Args:
        limit: Maximum number of messages to fetch

    Returns:
        List of parsed message dictionaries
    """
    global _client

    if not _client or not _client.is_ready:
        logger.warning("Discord client not ready")
        return []

    try:
        channel = _client.get_channel(int(_client.channel_id))
        if not channel:
            logger.warning(f"Could not find channel with ID {_client.channel_id}")
            return []

        messages = []
        async for message in channel.history(limit=limit):
            # Parse message
            parsed_data = parse_message(message.content)

            # Add message metadata
            parsed_data['message_id'] = str(message.id)
            parsed_data['author'] = str(message.author)
            parsed_data['timestamp'] = message.created_at.isoformat()

            messages.append(parsed_data)

        return messages

    except Exception as e:
        logger.error(f"Error fetching recent messages: {e}")
        return []