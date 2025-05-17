"""
Discord Message Fetcher

This module retrieves and stores raw messages from Discord channels,
specifically focused on fetching A+ trading setup messages.
"""
import os
import json
import logging
import asyncio
from datetime import datetime
import discord
import redis
import time

from common.redis_utils import get_redis_client, publish_event
from common.event_constants import EventType

logger = logging.getLogger(__name__)

# Get configuration from environment variables
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
CHANNEL_APLUS_SETUPS = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')

# Convert channel IDs to integers
try:
    CHANNEL_APLUS_SETUPS_ID = int(CHANNEL_APLUS_SETUPS) if CHANNEL_APLUS_SETUPS else None
except (ValueError, TypeError) as e:
    logger.error(f"Error converting Discord channel ID: {e}")
    CHANNEL_APLUS_SETUPS_ID = None


async def fetch_latest_messages(channel_id: int, limit: int = 50) -> list:
    """
    Fetch the latest messages from a Discord channel.
    
    Args:
        channel_id: The Discord channel ID to fetch messages from
        limit: Maximum number of messages to fetch (default: 50)
        
    Returns:
        List of message dictionaries with complete message data
    """
    if not DISCORD_BOT_TOKEN:
        logger.error("Discord bot token not found. Set DISCORD_BOT_TOKEN_APLUS environment variable.")
        return []
    
    messages = []
    
    try:
        # Create a client with message content intent enabled
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
        @client.event
        async def on_ready():
            try:
                logger.info(f"Connected to Discord as {client.user}")
                
                # Get the channel
                channel = client.get_channel(channel_id)
                if channel is None:
                    channel = await client.fetch_channel(channel_id)
                
                if not channel:
                    logger.error(f"Could not find channel with ID {channel_id}")
                    await client.close()
                    return
                    
                logger.info(f"Connected to Discord channel: {channel.name} (ID: {channel_id})")
                
                # Fetch messages
                message_count = 0
                async for msg in channel.history(limit=limit):
                    message_count += 1
                    
                    # Create a comprehensive message object with all data
                    message_data = {
                        'id': str(msg.id),
                        'author': str(msg.author),
                        'author_id': str(msg.author.id),
                        'content': msg.content,
                        'timestamp': msg.created_at.isoformat(),
                        'embeds': [],
                        'attachments': [],
                        'is_forwarded': False
                    }
                    
                    # Add attachment data
                    if msg.attachments:
                        for attachment in msg.attachments:
                            message_data['attachments'].append({
                                'id': str(attachment.id),
                                'filename': attachment.filename,
                                'url': attachment.url,
                                'content_type': attachment.content_type,
                                'size': attachment.size
                            })
                    
                    # Add embed data
                    if msg.embeds:
                        for embed in msg.embeds:
                            embed_data = {
                                'title': embed.title,
                                'description': embed.description,
                                'url': embed.url,
                                'timestamp': embed.timestamp.isoformat() if embed.timestamp else None,
                                'fields': []
                            }
                            
                            # Add embed fields
                            if hasattr(embed, 'fields'):
                                for field in embed.fields:
                                    embed_data['fields'].append({
                                        'name': field.name,
                                        'value': field.value,
                                        'inline': field.inline
                                    })
                            
                            message_data['embeds'].append(embed_data)
                    
                    # Handle forwarded/quoted messages
                    if hasattr(msg, 'reference') and msg.reference:
                        try:
                            # Get the original message that was forwarded/quoted
                            orig = None
                            if hasattr(msg.reference, 'resolved') and msg.reference.resolved:
                                orig = msg.reference.resolved
                            elif hasattr(msg.reference, 'message_id') and msg.reference.message_id:
                                try:
                                    orig = await channel.fetch_message(msg.reference.message_id)
                                except Exception as e:
                                    logger.warning(f"Could not fetch referenced message {msg.reference.message_id}: {e}")
                            
                            if orig:
                                # Mark as forwarded and add the forwarded message data
                                message_data['is_forwarded'] = True
                                
                                # Create the forwarded object with the original message's data
                                forwarded_data = {
                                    'id': str(orig.id),
                                    'author': str(orig.author),
                                    'author_id': str(orig.author.id) if hasattr(orig.author, 'id') else None,
                                    'content': orig.content,
                                    'timestamp': orig.created_at.isoformat(),
                                    'embeds': [],
                                    'attachments': []
                                }
                                
                                # Add the original message's attachments
                                if orig.attachments:
                                    for attachment in orig.attachments:
                                        forwarded_data['attachments'].append({
                                            'id': str(attachment.id),
                                            'filename': attachment.filename,
                                            'url': attachment.url,
                                            'content_type': attachment.content_type,
                                            'size': attachment.size
                                        })
                                
                                # Add the original message's embeds
                                if orig.embeds:
                                    for embed in orig.embeds:
                                        embed_data = {
                                            'title': embed.title,
                                            'description': embed.description,
                                            'url': embed.url,
                                            'timestamp': embed.timestamp.isoformat() if embed.timestamp else None,
                                            'fields': []
                                        }
                                        
                                        # Add embed fields
                                        if hasattr(embed, 'fields'):
                                            for field in embed.fields:
                                                embed_data['fields'].append({
                                                    'name': field.name,
                                                    'value': field.value,
                                                    'inline': field.inline
                                                })
                                        
                                        forwarded_data['embeds'].append(embed_data)
                                
                                # Add the forwarded data to the message
                                message_data['forwarded'] = forwarded_data
                                logger.info(f"Detected forwarded message: {msg.id} references {orig.id}")
                        except Exception as e:
                            logger.error(f"Error processing forwarded message {msg.id}: {e}")
                    
                    messages.append(message_data)
                    logger.debug(f"Fetched message {msg.id} from {msg.author}")
                
                logger.info(f"Successfully fetched {message_count} messages from channel {channel_id}")
                
                # Disconnect after we're done
                await client.close()
                
            except Exception as e:
                logger.error(f"Error fetching messages from channel {channel_id}: {e}")
                await client.close()
        
        # Start the client and run until complete
        await client.start(DISCORD_BOT_TOKEN)
        
    except Exception as e:
        logger.error(f"Error connecting to Discord: {e}")
    
    return messages


def store_raw_messages(messages: list, filename: str = "setups_raw.json") -> bool:
    """
    Store raw Discord messages to a file as JSON.
    
    Args:
        messages: List of message dictionaries to store
        filename: Filename to store the messages (default: setups_raw.json)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        # Write messages to file
        with open(filename, 'w') as f:
            json.dump(messages, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error storing messages to {filename}: {e}")
        return False

def store_message_in_redis(message: dict, stream_key: str = "discord:messages") -> bool:
    """
    Store a single message in Redis Stream.
    
    Args:
        message: Message dictionary to store
        stream_key: Redis Stream key (default: discord:messages)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get Redis client
        redis_client = get_redis_client()
        
        # Convert message to flat structure for Redis Stream
        # Redis Streams require data in the form of field-value pairs
        flat_message = {
            'id': message['id'],
            'author': message['author'],
            'content': message['content'],
            'timestamp': message['timestamp'],
            'json_data': json.dumps(message)  # Store the full JSON object
        }
        
        # Add message to Redis Stream
        if not redis_client.fallback_mode:
            # Use native Redis
            message_id = redis_client.client.xadd(stream_key, flat_message)
            logger.info(f"Added message {message['id']} to Redis Stream {stream_key} with ID {message_id}")
        else:
            # Using fallback mode, store in a sorted set with timestamp as score
            timestamp = time.time()
            key = f"{stream_key}:{timestamp}:{message['id']}"
            redis_client.set(key, json.dumps(message))
            logger.info(f"Added message {message['id']} to fallback storage with key {key}")
        
        # Publish an event to notify consumers
        event_data = {
            'event_type': 'discord.message.created',
            'message_id': message['id'],
            'stream_key': stream_key,
            'timestamp': message['timestamp']
        }
        publish_event('events:discord:message', event_data)
        
        return True
    except Exception as e:
        logger.error(f"Error storing message in Redis: {e}")
        return False


def fetch_and_store_setups(limit: int = 50, filename: str = "setups_raw.json") -> int:
    """
    Fetches and stores raw setup messages from the A+ setups Discord channel.
    
    Args:
        limit: Maximum number of messages to fetch (default: 50)
        filename: Filename to store the raw JSON (default: setups_raw.json)
        
    Returns:
        Number of messages stored
    """
    if not CHANNEL_APLUS_SETUPS_ID:
        logger.error("A+ setups channel ID not configured. Set DISCORD_CHANNEL_APLUS_SETUPS environment variable.")
        return 0
    
    try:
        # Create an event loop to run our async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Fetch messages from Discord
        messages = loop.run_until_complete(
            fetch_latest_messages(CHANNEL_APLUS_SETUPS_ID, limit)
        )
        loop.close()
        
        if not messages:
            logger.warning("No messages fetched from Discord")
            return 0
        
        # Store messages to file
        if store_raw_messages(messages, filename):
            message_count = len(messages)
            logger.info(f"Fetched {message_count} messages; stored to {filename}")
            return message_count
        else:
            logger.error(f"Failed to store messages to {filename}")
            return 0
        
    except Exception as e:
        logger.error(f"Error fetching and storing setup messages: {e}")
        return 0


if __name__ == "__main__":
    import sys
    
    # Configure logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Default settings
    limit = 50
    output_file = "setups_raw.json"
    
    # Parse command line arguments if provided
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Invalid limit value: {sys.argv[1]}. Using default: {limit}")
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Print configuration info
    print(f"Discord A+ Setups Message Fetcher")
    print(f"================================")
    print(f"Bot Token: {DISCORD_BOT_TOKEN[:5]}*** (truncated)" if DISCORD_BOT_TOKEN else "Bot Token: Not configured")
    print(f"A+ Setups Channel ID: {CHANNEL_APLUS_SETUPS_ID}" if CHANNEL_APLUS_SETUPS_ID else "A+ Setups Channel ID: Not configured")
    print(f"Fetch Limit: {limit}")
    print(f"Output File: {output_file}")
    print(f"================================")
    
    # Check if required environment variables are set
    if not DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN_APLUS environment variable is not set.")
        print("Please set it to your Discord bot token and try again.")
        sys.exit(1)
    
    if not CHANNEL_APLUS_SETUPS_ID:
        print("Error: DISCORD_CHANNEL_APLUS_SETUPS environment variable is not set.")
        print("Please set it to the ID of the A+ Setups channel and try again.")
        sys.exit(1)
    
    # Fetch and store the messages
    print("Fetching messages from Discord...")
    count = fetch_and_store_setups(limit=limit, filename=output_file)
    
    if count > 0:
        print(f"[INFO] Fetched {count} messages; stored to {output_file}")
        
        # Verify file was created
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"File created successfully: {output_file} ({size} bytes)")
        else:
            print(f"Warning: Expected output file {output_file} was not created.")
    else:
        print(f"Failed to fetch messages from Discord. Check logs for details.")