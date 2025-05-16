"""
Discord Client Module

This module provides functionality for interacting with Discord,
including sending and reading messages from specific channels.
"""
import os
import logging
import asyncio
from typing import Optional, List, Callable, Any
from functools import wraps
from datetime import datetime, timedelta
import discord
from discord.ext import tasks

logger = logging.getLogger(__name__)

# Get configuration from environment variables
DISCORD_APP_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
CHANNEL_BOT_DIALOGUE = os.environ.get('DISCORD_CHANNEL_BOT_DIALOGUE')
CHANNEL_APLUS_SETUPS = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')

# Convert channel IDs to integers
try:
    CHANNEL_BOT_DIALOGUE_ID = int(CHANNEL_BOT_DIALOGUE) if CHANNEL_BOT_DIALOGUE else None
    CHANNEL_APLUS_SETUPS_ID = int(CHANNEL_APLUS_SETUPS) if CHANNEL_APLUS_SETUPS else None
except (ValueError, TypeError) as e:
    logger.error(f"Error converting Discord channel IDs: {e}")
    CHANNEL_BOT_DIALOGUE_ID = None
    CHANNEL_APLUS_SETUPS_ID = None

# Initialize client as None
discord_client = None
client_ready = False
message_handlers = []
setup_message_callbacks = []
is_discord_available = bool(DISCORD_APP_TOKEN and CHANNEL_APLUS_SETUPS_ID)

def register_message_handler(handler: Callable[[discord.Message], Any]) -> None:
    """
    Register a function to handle new messages.
    
    Args:
        handler: Function that takes a Discord message and processes it
    """
    message_handlers.append(handler)

def register_setup_callback(callback: Callable[[str, datetime], Any]) -> None:
    """
    Register a callback for when a new trading setup is detected.
    
    Args:
        callback: Function that takes message content and timestamp
    """
    setup_message_callbacks.append(callback)

def requires_discord(f):
    """
    Decorator to check if Discord is available before running a function.
    If Discord is not available, logs a warning and returns None.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_discord_available:
            logger.warning(f"Discord functionality unavailable - skipping {f.__name__}")
            return None
        return f(*args, **kwargs)
    return decorated

class APlusTradingClient(discord.Client):
    """A+ Trading Discord client to monitor and send messages."""
    
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True  # Enable message content intent
        super().__init__(intents=intents, *args, **kwargs)
        self.setup_checks = self.check_for_setups.start()
        self.last_checked_time = datetime.utcnow() - timedelta(hours=24)  # Start by checking last 24h
        
    async def on_ready(self):
        """Called when the client has successfully connected to Discord."""
        global client_ready
        client_ready = True
        logger.info(f'Discord bot logged in as {self.user}')
        
        # Send a message to the bot dialogue channel
        if CHANNEL_BOT_DIALOGUE_ID:
            channel = self.get_channel(CHANNEL_BOT_DIALOGUE_ID)
            if channel:
                await channel.send('A+ Trading Bot is now online and monitoring for trading setups.')
            else:
                logger.warning(f"Could not find bot dialogue channel with ID {CHANNEL_BOT_DIALOGUE_ID}")
        
    async def on_message(self, message):
        """Called when a new message is received."""
        # Don't respond to our own messages
        if message.author == self.user:
            return
            
        # Process message through all handlers
        for handler in message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    @tasks.loop(minutes=5)
    async def check_for_setups(self):
        """Check for new trading setup messages periodically."""
        if not CHANNEL_APLUS_SETUPS_ID:
            return
            
        try:
            channel = self.get_channel(CHANNEL_APLUS_SETUPS_ID)
            if not channel:
                logger.warning(f"Could not find A+ setups channel with ID {CHANNEL_APLUS_SETUPS_ID}")
                return
                
            # Get messages after the last checked time
            current_time = datetime.utcnow()
            async for message in channel.history(after=self.last_checked_time, limit=20):
                # Check if message has content and is not from our bot
                if message.content and message.author != self.user:
                    # Check if message looks like a trading setup
                    if "A+ Trade Setups" in message.content:
                        # Call all setup callbacks
                        logger.info(f"Found new trading setup message: {message.id}")
                        for callback in setup_message_callbacks:
                            try:
                                # Pass message content and timestamp to callback
                                callback(message.content, message.created_at)
                            except Exception as e:
                                logger.error(f"Error in setup message callback: {e}")
            
            # Update the last checked time
            self.last_checked_time = current_time
            
        except Exception as e:
            logger.error(f"Error checking for trading setups: {e}")
    
    @check_for_setups.before_loop
    async def before_check_for_setups(self):
        """Wait until the bot is ready before starting the task loop."""
        await self.wait_until_ready()

@requires_discord
def initialize_discord_client():
    """Initialize the Discord client if credentials are available."""
    global discord_client
    
    if not DISCORD_APP_TOKEN:
        logger.warning("Discord bot token not found in environment variables")
        return False
        
    if not (CHANNEL_BOT_DIALOGUE_ID and CHANNEL_APLUS_SETUPS_ID):
        logger.warning("Discord channel IDs not properly configured")
        return False
    
    try:
        # Create client
        discord_client = APlusTradingClient()
        
        # Start in a new thread to avoid blocking
        import threading
        
        def run_discord_client():
            """Run Discord client in a separate thread."""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the client
                if DISCORD_APP_TOKEN:
                    discord_client.loop = loop
                    loop.run_until_complete(discord_client.start(DISCORD_APP_TOKEN))
                else:
                    logger.error("Discord token is not available")
            except Exception as e:
                logger.error(f"Error in Discord client thread: {e}")
        
        # Start thread
        client_thread = threading.Thread(target=run_discord_client, daemon=True)
        client_thread.start()
        
        logger.info("Discord client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Discord client: {e}")
        return False

@requires_discord
def send_message(channel_id: int, message: str) -> bool:
    """
    Send a message to a Discord channel.
    
    Args:
        channel_id: Discord channel ID
        message: Message content to send
        
    Returns:
        bool: Success or failure
    """
    if not discord_client or not client_ready:
        logger.warning("Discord client not ready, message not sent")
        return False
    
    # Submit the message to be sent asynchronously
    future_message = asyncio.run_coroutine_threadsafe(
        _send_message_async(channel_id, message),
        discord_client.loop
    )
    
    try:
        # Wait for a short time for the message to be sent
        return future_message.result(timeout=5)
    except asyncio.TimeoutError:
        logger.error("Timeout while sending Discord message")
        return False
    except Exception as e:
        logger.error(f"Error sending Discord message: {e}")
        return False

async def _send_message_async(channel_id: int, message: str) -> bool:
    """
    Internal async function to send a message.
    
    Args:
        channel_id: Discord channel ID
        message: Message content to send
        
    Returns:
        bool: Success or failure
    """
    try:
        channel = discord_client.get_channel(channel_id)
        if not channel:
            logger.warning(f"Channel with ID {channel_id} not found")
            return False
            
        await channel.send(message)
        return True
    except Exception as e:
        logger.error(f"Error in async message sending: {e}")
        return False

@requires_discord
def send_bot_message(message: str) -> bool:
    """
    Send a message to the bot dialogue channel.
    
    Args:
        message: Message content to send
        
    Returns:
        bool: Success status (or None if Discord unavailable)
    """
    if not CHANNEL_BOT_DIALOGUE_ID:
        logger.warning("Bot dialogue channel ID not configured")
        return False
    
    return send_message(CHANNEL_BOT_DIALOGUE_ID, message)

@requires_discord
def send_status_update(message: str) -> bool:
    """
    Send a status update to the bot dialogue channel.
    
    Args:
        message: Status update message
        
    Returns:
        bool: Success status (or None if Discord unavailable)
    """
    formatted_message = f"**Status Update**: {message}"
    return send_bot_message(formatted_message)

@requires_discord
def send_trade_alert(symbol: str, alert_type: str, details: str) -> bool:
    """
    Send a trade alert to the bot dialogue channel.
    
    Args:
        symbol: Stock symbol
        alert_type: Type of alert (entry, exit, etc.)
        details: Alert details
        
    Returns:
        bool: Success status (or None if Discord unavailable)
    """
    formatted_message = f"**Trade Alert [{symbol}]**: {alert_type}\n{details}"
    return send_bot_message(formatted_message)

@requires_discord
def send_error_notification(error_type: str, details: str) -> bool:
    """
    Send an error notification to the bot dialogue channel.
    
    Args:
        error_type: Type of error
        details: Error details
        
    Returns:
        bool: Success status (or None if Discord unavailable)
    """
    formatted_message = f"**Error [{error_type}]**: {details}"
    return send_bot_message(formatted_message)

def is_client_ready() -> bool:
    """Check if the Discord client is ready."""
    return client_ready