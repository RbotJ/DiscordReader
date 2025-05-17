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
DISCORD_APP_TOKEN = os.environ.get('DISCORD_BOT_TOKEN_APLUS') or os.environ.get('DISCORD_BOT_TOKEN')
CHANNEL_BOT_DIALOGUE = os.environ.get('DISCORD_CHANNEL_BOT_DIALOGUE')
CHANNEL_APLUS_SETUPS = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
CHANNEL_TEST = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')

# Convert channel IDs to integers
try:
    CHANNEL_BOT_DIALOGUE_ID = int(CHANNEL_BOT_DIALOGUE) if CHANNEL_BOT_DIALOGUE else None
    CHANNEL_APLUS_SETUPS_ID = int(CHANNEL_APLUS_SETUPS) if CHANNEL_APLUS_SETUPS else None
    CHANNEL_TEST_ID = int(CHANNEL_TEST) if CHANNEL_TEST else None
except (ValueError, TypeError) as e:
    logger.error(f"Error converting Discord channel IDs: {e}")
    CHANNEL_BOT_DIALOGUE_ID = None
    CHANNEL_APLUS_SETUPS_ID = None
    CHANNEL_TEST_ID = None

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
        discord_client = APlusTradingClient()
        
        # Run the bot in a separate thread to avoid blocking
        def _run_bot():
            try:
                discord_client.run(DISCORD_APP_TOKEN)
            except Exception as e:
                logger.error(f"Error in Discord bot thread: {e}")
                
        import threading
        thread = threading.Thread(target=_run_bot, daemon=True)
        thread.start()
        
        logger.info("Discord client initialized and running")
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
    if not client_ready or not discord_client:
        logger.warning("Discord client not ready")
        return False

    chan = discord_client.get_channel(channel_id)
    if not chan:
        logger.error(f"Channel {channel_id} not found")
        return False

    try:
        # Schedule the coroutine in the bot's event loop
        future = asyncio.run_coroutine_threadsafe(
            chan.send(message),
            discord_client.loop
        )
        future.result(timeout=10)
        logger.info(f"Message sent to channel {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
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

@requires_discord
def send_test_message(message: str) -> bool:
    """
    Send a message to the test channel.
    
    Args:
        message: Message to send
    
    Returns:
        bool: Success status (or None if Discord unavailable)
    """
    if not CHANNEL_TEST_ID:
        logger.warning("Test channel ID not configured")
        return False
    
    return send_message(CHANNEL_TEST_ID, message)

def is_client_ready() -> bool:
    """Check if the Discord client is ready."""
    return client_ready

@requires_discord
def get_channel_messages() -> List[dict]:
    """
    Get recent messages from the A+ setups channel.
    
    Returns:
        List of message dictionaries with 'content' and 'timestamp' keys
    """
    if not CHANNEL_APLUS_SETUPS_ID:
        logger.warning("A+ setups channel ID not configured")
        return []
    
    # Check if we have a valid Discord token
    if not DISCORD_APP_TOKEN:
        logger.warning("Discord bot token not configured")
        return []
    
    try:
        import asyncio
        import discord
        
        async def fetch_latest_messages():
            # Create a client with message content intent enabled
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message content
            client = discord.Client(intents=intents)
            
            messages = []
            
            @client.event
            async def on_ready():
                try:
                    # Try to get the channel from cache, else fetch it
                    channel = client.get_channel(CHANNEL_APLUS_SETUPS_ID)
                    if channel is None:
                        channel = await client.fetch_channel(CHANNEL_APLUS_SETUPS_ID)
                    
                    logger.info(f"Fetching messages from Discord channel: #{channel.name} (ID: {CHANNEL_APLUS_SETUPS_ID})")
                    
                    # Fetch more messages to ensure we capture all the recent trading setups
                    message_count = 0
                    async for msg in channel.history(limit=20):
                        # Include all messages, even if they have empty content
                        # This way, we can see what's actually in the channel
                        message_count += 1
                        logger.info(f"Found message from Discord: {msg.id} from {msg.author}, content length: {len(msg.content)}")
                        
                        # Check for attachments or embeds
                        attachments_info = []
                        if msg.attachments:
                            for attachment in msg.attachments:
                                attachments_info.append(f"[Attachment: {attachment.filename}]")
                        
                        embeds_info = []
                        if msg.embeds:
                            for embed in msg.embeds:
                                embed_desc = embed.description or "No description"
                                embed_title = embed.title or "No title"
                                embeds_info.append(f"[Embed: {embed_title} - {embed_desc[:50]}...]")
                        
                        # Create a combined content that includes info about attachments/embeds
                        combined_content = msg.content
                        
                        # Check for forwarded messages in embeds
                        if hasattr(msg, 'embeds') and msg.embeds:
                            for embed in msg.embeds:
                                # Forwarded messages typically store the content in the description
                                if hasattr(embed, 'description') and embed.description:
                                    if not combined_content:  # If content is empty, use embed description
                                        combined_content = embed.description
                                        logger.info(f"Found content in embed.description: {combined_content[:50]}...")
                                    else:  # Otherwise append it
                                        combined_content += f"\n\n{embed.description}"
                                        
                                # Some embeds might have fields with additional information
                                if hasattr(embed, 'fields') and embed.fields:
                                    for field in embed.fields:
                                        field_content = f"{field.name}: {field.value}" if hasattr(field, 'name') and hasattr(field, 'value') else ""
                                        if field_content:
                                            if combined_content:
                                                combined_content += f"\n{field_content}"
                                            else:
                                                combined_content = field_content
                        
                        # Add attachment and embed info
                        if attachments_info or embeds_info:
                            if combined_content:
                                combined_content += "\n\n"
                            combined_content += "\n".join(attachments_info + embeds_info)
                        
                        # Check for message_snapshots which might contain the actual content
                        # Try to extract content from message_snapshots
                        try:
                            # Check for message_snapshots - we need to handle these specially
                            if hasattr(msg, 'message_snapshots') and msg.message_snapshots:
                                logger.info(f"Found message_snapshots in message {msg.id}")
                                
                                # Try to access the raw data of message_snapshots
                                try:
                                    if isinstance(msg.message_snapshots, list):
                                        # Convert to string to see the raw data
                                        snapshots_str = str(msg.message_snapshots)
                                        logger.info(f"Message snapshots (raw): {snapshots_str[:200]}...")
                                        
                                        # Try to extract content via various methods
                                        for i, snapshot in enumerate(msg.message_snapshots):
                                            logger.info(f"Processing snapshot {i}")
                                            
                                            # Try using __dict__ to get all attributes
                                            if hasattr(snapshot, '__dict__'):
                                                logger.info(f"Snapshot {i} dict: {str(snapshot.__dict__)[:200]}...")
                                            
                                            try:
                                                # Try direct string representation for debugging
                                                snapshot_str = str(snapshot)
                                                logger.info(f"Snapshot {i} string: {snapshot_str[:200]}...")
                                                
                                                # Look for content in the snapshot string
                                                if "content" in snapshot_str and "Trade Setups" in snapshot_str:
                                                    # Extract content from the snapshot string
                                                    parts = snapshot_str.split("'content': '")
                                                    if len(parts) > 1:
                                                        content_part = parts[1].split("'", 1)[0]
                                                        if content_part:
                                                            combined_content = content_part
                                                            logger.info(f"Extracted content from snapshot string: {combined_content[:50]}...")
                                                            break
                                            except Exception as extract_err:
                                                logger.error(f"Error extracting content from snapshot string: {extract_err}")
                                            
                                            # Try accessing the message property in different ways
                                            try:
                                                # Method 1: Try as dict
                                                if isinstance(snapshot, dict) and 'message' in snapshot:
                                                    if isinstance(snapshot['message'], dict) and 'content' in snapshot['message']:
                                                        combined_content = snapshot['message']['content']
                                                        logger.info(f"Found content in snapshot['message']['content']: {combined_content[:50]}...")
                                                        break
                                                
                                                # Method 2: Try as object
                                                if hasattr(snapshot, 'message'):
                                                    msg_obj = getattr(snapshot, 'message')
                                                    logger.info(f"Found message object in snapshot: {type(msg_obj)}")
                                                    
                                                    if isinstance(msg_obj, dict) and 'content' in msg_obj:
                                                        combined_content = msg_obj['content']
                                                        logger.info(f"Found content in snapshot.message dict: {combined_content[:50]}...")
                                                        break
                                                    
                                                    if hasattr(msg_obj, 'content'):
                                                        content = getattr(msg_obj, 'content')
                                                        if content:
                                                            combined_content = content
                                                            logger.info(f"Found content in snapshot.message.content: {combined_content[:50]}...")
                                                            break
                                            except Exception as access_err:
                                                logger.error(f"Error accessing message in snapshot: {access_err}")
                                except Exception as list_err:
                                    logger.error(f"Error processing message_snapshots list: {list_err}")
                        except Exception as e:
                            logger.error(f"Error extracting from message_snapshots: {e}")
                            if hasattr(msg, 'type'):
                                logger.info(f"Message type: {msg.type}")
                            if hasattr(msg, 'flags'):
                                logger.info(f"Message flags: {msg.flags}")
                        
                        # If still empty, note that it's empty
                        if not combined_content:
                            combined_content = "(Message contains no text content or attachments)"
                        
                        messages.append({
                            'id': str(msg.id),
                            'content': combined_content,
                            'timestamp': msg.created_at,
                            'author': str(msg.author),
                            'has_snapshots': hasattr(msg, 'message_snapshots') and bool(msg.message_snapshots)
                        })
                    
                    logger.info(f"Fetched {message_count} messages, {len(messages)} with content")
                    
                    if not messages:
                        logger.warning(f"No messages found in channel {CHANNEL_APLUS_SETUPS_ID}")
                
                except Exception as e:
                    logger.error(f"Error fetching messages from Discord: {e}")
                
                finally:
                    # Disconnect once done
                    await client.close()
            
            # Start the client and run it until it disconnects
            try:
                await client.start(DISCORD_APP_TOKEN)
            except Exception as e:
                logger.error(f"Error starting Discord client: {e}")
            
            return messages
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fetch_latest_messages())
        loop.close()
        
        if result:
            logger.info(f"Successfully fetched {len(result)} messages from Discord")
            return result
        else:
            logger.warning("No messages found in Discord channel, returning empty list")
            return []
    
    except Exception as e:
        logger.error(f"Error in Discord message fetching: {e}")
        # Return an empty list if anything fails
        return []