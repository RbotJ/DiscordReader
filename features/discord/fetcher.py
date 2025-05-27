
"""
Discord Message Fetcher

Consolidated Discord.py client logic for fetching messages
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
import discord

logger = logging.getLogger(__name__)

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS', 0))

async def fetch_latest_messages(limit: int = 50) -> List[Dict]:
    """
    Fetch latest messages from Discord channel
    
    Args:
        limit: Maximum number of messages to fetch
        
    Returns:
        List of message dictionaries
    """
    if not DISCORD_BOT_TOKEN or not CHANNEL_ID:
        logger.error("Missing Discord configuration")
        return []

    messages = []
    retry_attempts = 3

    for attempt in range(retry_attempts):
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)

            @client.event
            async def on_ready():
                try:
                    channel = client.get_channel(CHANNEL_ID)
                    if not channel:
                        channel = await client.fetch_channel(CHANNEL_ID)

                    async for msg in channel.history(limit=limit):
                        message_data = {
                            'id': str(msg.id),
                            'content': msg.content,
                            'author': str(msg.author),
                            'author_id': str(msg.author.id),
                            'channel_id': str(msg.channel.id),
                            'timestamp': msg.created_at.isoformat(),
                            'attachments': [
                                {'url': a.url, 'filename': a.filename}
                                for a in msg.attachments
                            ]
                        }
                        messages.append(message_data)

                    await client.close()
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    await client.close()

            await client.start(DISCORD_BOT_TOKEN)
            if messages:
                break

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retry_attempts - 1:
                logger.error("All retry attempts failed")
            await asyncio.sleep(1)

    return messages
