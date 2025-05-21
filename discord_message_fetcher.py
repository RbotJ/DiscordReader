#!/usr/bin/env python3
"""
Discord Message Fetcher

A simple script to fetch the most recent message from the A+ Trading Discord channel.
Uses discord.py library to directly pull messages using the bot token.
Stores messages in the PostgreSQL database.
"""
import os
import asyncio
import logging
from datetime import datetime
import discord

# Import database utilities
from db_utils import store_discord_message, get_message_stats_from_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_discord_message():
    """Fetch the most recent message from the configured Discord channel."""
    # Grab token and channel ID from environment
    token = os.getenv('DISCORD_APP_TOKEN') or os.getenv('DISCORD_BOT_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_APLUS_SETUPS')
    
    if not token:
        logger.error("DISCORD_APP_TOKEN or DISCORD_BOT_TOKEN environment variable not set")
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
            
            # Pull the latest messages
            messages_found = 0
            async for msg in channel.history(limit=5):
                # Print out what we found to help debug
                logger.info(f"Found message: {msg.id} from {msg.author}")
                logger.info(f"Content length: {len(msg.content)}")
                if len(msg.content) > 0:
                    logger.info(f"Content: {msg.content}")
                
                # Store the first message (most recent)
                if messages_found == 0:
                    message_data['id'] = str(msg.id)
                    message_data['author'] = str(msg.author)
                    message_data['timestamp'] = msg.created_at.isoformat()
                    message_data['content'] = msg.content
                    message_data['channel_name'] = channel.name
                    
                messages_found += 1
            
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

async def fetch_and_store_message():
    """Fetch and store a Discord message in the database."""
    # Fetch the message
    message_data = await fetch_discord_message()
    
    if not message_data:
        logger.error("Failed to fetch Discord message")
        return False
    
    # Store the message in the database
    success = store_discord_message(message_data)
    
    if success:
        logger.info("Successfully stored Discord message in database")
        # Get updated stats
        stats = get_message_stats_from_database()
        logger.info(f"Total messages in database: {stats['count']}")
        return True
    else:
        logger.error("Failed to store Discord message in database")
        return False

def main():
    """Run the script to fetch the most recent Discord message."""
    # Run the async function
    success = asyncio.run(fetch_and_store_message())
    
    if success:
        print("\n===== DISCORD MESSAGE SUCCESSFULLY STORED IN DATABASE =====")
        # Display database stats
        stats = get_message_stats_from_database()
        print(f"Total messages in database: {stats['count']}")
        
        if stats.get('latest_id'):
            print(f"Latest message ID: {stats['latest_id']}")
            print(f"Latest message date: {stats['latest_date']}")
    else:
        print("Failed to fetch or store Discord message.")

if __name__ == "__main__":
    main()