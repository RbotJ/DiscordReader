"""
Simple Discord Message Fetcher

A focused script to fetch the most recent message from the A+ Trading Discord channel.
Uses discord.py library to directly pull messages using the bot token.
"""
import asyncio
import os
import json
import logging
from datetime import datetime

import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Discord configuration
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID") 
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

# Set up storage for the latest message
LATEST_MESSAGE_FILE = "latest_discord_message.json"

from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import DiscordMessageModel

async def fetch_latest_discord_message():
    """Fetch the most recent message from the configured Discord channel."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables")
        return None

    if not DISCORD_CHANNEL_ID:
        logger.error("DISCORD_CHANNEL_ID not found in environment variables")
        return None

    # Create a Discord client with the necessary intents
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="!", intents=intents)

    @client.event
    async def on_ready():
        logger.info(f"Logged in as {client.user}")

        try:
            # Get the channel by ID
            channel_id = int(DISCORD_CHANNEL_ID)
            channel = client.get_channel(channel_id)

            if not channel:
                logger.error(f"Channel with ID {channel_id} not found")
                await client.close()
                return

            logger.info(f"Fetching messages from channel: {channel.name}")

            # Fetch the most recent message
            async for message in channel.history(limit=1):
                logger.info(f"Found message: {message.content}")

                # Format message data
                message_data = {
                    "id": str(message.id),
                    "content": message.content,
                    "author": str(message.author),
                    "timestamp": message.created_at.isoformat(),
                    "channel_name": channel.name,
                    "fetch_timestamp": datetime.now().isoformat()
                }

                # Import the storage module to save the message
                try:
                    # Save message to database
                    discord_message = DiscordMessageModel(**message_data)
                    db.session.add(discord_message)
                    db.session.commit()

                    logger.info(f"Message saved to database.")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error saving message to database: {e}")
                    # Fallback to just saving the latest message file
                    with open(LATEST_MESSAGE_FILE, 'w') as f:
                        json.dump(message_data, f, indent=2)
                    logger.warning(f"Used fallback storage method - saved only to {LATEST_MESSAGE_FILE}")

            await client.close()

        except Exception as e:
            logger.error(f"Error fetching Discord message: {e}")
            await client.close()

    try:
        await client.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting Discord client: {e}")

def get_latest_discord_message():
    """Get the latest Discord message from database if it exists."""
    try:
        latest_message = DiscordMessageModel.query.order_by(DiscordMessageModel.timestamp.desc()).first()
        if latest_message:
            return {
                "id": str(latest_message.id),
                "content": latest_message.content,
                "author": str(latest_message.author),
                "timestamp": latest_message.timestamp,
                "channel_name": latest_message.channel_name,
                "fetch_timestamp": latest_message.fetch_timestamp
            }
        return None
    except Exception as e:
        logger.error(f"Error reading latest Discord message from database: {e}")
        return None

def fetch_discord_message():
    """Run the asynchronous function to fetch Discord message."""
    asyncio.run(fetch_latest_discord_message())
    return get_latest_discord_message()

if __name__ == "__main__":
    # Fetch and print the most recent Discord message
    message = fetch_discord_message()
    if message:
        print(f"Latest message from {message['channel_name']} by {message['author']} at {message['timestamp']}:")
        print(message['content'])
    else:
        print("No message found or error occurred.")