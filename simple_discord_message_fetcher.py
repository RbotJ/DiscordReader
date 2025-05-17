#!/usr/bin/env python3
"""
Simple Discord Message Fetcher

This script fetches recent messages from a Discord channel using discord.py.
"""
import os
import asyncio
import discord
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fetch_discord_messages():
    """Fetch recent messages from a Discord channel."""
    # Get Discord token and channel ID from environment variables
    token = os.getenv('DISCORD_BOT_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_APLUS_SETUPS')
    
    if not token or not channel_id:
        logger.error("Missing required environment variables DISCORD_BOT_TOKEN or DISCORD_CHANNEL_APLUS_SETUPS")
        return []
    
    try:
        channel_id = int(channel_id)
    except ValueError:
        logger.error("DISCORD_CHANNEL_APLUS_SETUPS must be an integer")
        return []
    
    # Create Discord client with minimal intents
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    messages = []
    
    @client.event
    async def on_ready():
        logger.info(f"Connected to Discord as {client.user}")
        try:
            # Get the target channel
            channel = client.get_channel(channel_id)
            if not channel:
                logger.info(f"Channel {channel_id} not found in cache, trying to fetch it")
                channel = await client.fetch_channel(channel_id)
            
            logger.info(f"Fetching messages from channel: {channel.name} (ID: {channel_id})")
            
            # Fetch recent messages (up to 10)
            async for message in channel.history(limit=10):
                messages.append({
                    'id': str(message.id),
                    'author': str(message.author),
                    'content': message.content,
                    'timestamp': message.created_at
                })
                logger.info(f"Found message: {message.id} from {message.author}")
            
            logger.info(f"Fetched {len(messages)} messages successfully")
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
        finally:
            # Disconnect once we're done
            await client.close()
    
    try:
        # Connect to Discord
        await client.start(token)
    except KeyboardInterrupt:
        await client.close()
    except Exception as e:
        logger.error(f"Error connecting to Discord: {e}")
    
    return messages

def main():
    """Main entry point for script."""
    try:
        loop = asyncio.get_event_loop()
        messages = loop.run_until_complete(fetch_discord_messages())
        
        if messages:
            print("\n=== Discord Messages ===")
            for i, msg in enumerate(messages, 1):
                print(f"\nMessage {i}:")
                print(f"  Author: {msg.get('author')}")
                print(f"  Time: {msg.get('timestamp').strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"  Content:\n{msg.get('content')}")
        else:
            print("No messages were fetched.")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()