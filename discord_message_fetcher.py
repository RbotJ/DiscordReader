#!/usr/bin/env python3
"""
Discord Message Fetcher

A simple script to fetch the most recent message from the A+ Trading Discord channel.
Uses discord.py library to directly pull messages using the bot token.
"""
import os
import asyncio
import logging
from datetime import datetime
import discord

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_discord_message():
    """Fetch the most recent message from the configured Discord channel."""
    # Grab token and channel ID from environment
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_APLUS_SETUPS')
    
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        return None
        
    if not channel_id:
        logger.error("DISCORD_CHANNEL_APLUS_SETUPS environment variable not set")
        return None
    
    try:
        channel_id = int(channel_id)
    except ValueError:
        logger.error("DISCORD_CHANNEL_APLUS_SETUPS must be an integer channel ID")
        return None
        
    # Create a client with minimal intents
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    message_data = {}
    
    @client.event
    async def on_ready():
        try:
            logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
            
            # Try to get the channel from cache, else fetch it
            channel = client.get_channel(channel_id)
            if channel is None:
                channel = await client.fetch_channel(channel_id)
                
            logger.info(f"Fetching messages from channel: #{channel.name} (ID: {channel_id})")
            
            # Pull the last message that contains "A+ Trade Setups"
            async for msg in channel.history(limit=10):
                if "A+ Trade Setups" in msg.content:
                    message_data['id'] = str(msg.id)
                    message_data['author'] = str(msg.author)
                    message_data['timestamp'] = msg.created_at.isoformat()
                    message_data['content'] = msg.content
                    logger.info(f"Found trading setup message (ID: {msg.id})")
                    break
            
            if not message_data:
                logger.warning(f"No trading setup messages found in channel {channel_id}")
                
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            
        finally:
            # Disconnect after we're done
            await client.close()
    
    try:
        # Start the client and run it until it disconnects
        await client.start(token)
    except Exception as e:
        logger.error(f"Error starting Discord client: {e}")
    
    return message_data

def main():
    """Run the script to fetch the most recent Discord message."""
    # Run the async function
    message = asyncio.run(fetch_discord_message())
    
    if message:
        print("\n===== MOST RECENT TRADING SETUP MESSAGE =====")
        print(f"ID:        {message['id']}")
        print(f"Author:    {message['author']}")
        print(f"Timestamp: {datetime.fromisoformat(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nContent:")
        print("----------------------------------------")
        print(message['content'])
        print("----------------------------------------")
    else:
        print("No trading setup message found or there was an error fetching messages.")

if __name__ == "__main__":
    main()