"""
Discord Message Fetcher with PostgreSQL storage
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
import discord
from sqlalchemy.exc import SQLAlchemyError

from app import db
from .models import DiscordMessageModel
from common.events import publish_event
from common.event_constants import EventType

logger = logging.getLogger(__name__)

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS', 0))

def validate_message(message: Dict) -> bool:
    """Validate required message fields exist"""
    required_fields = ['id', 'content', 'author', 'timestamp']
    return all(field in message for field in required_fields)

async def fetch_latest_messages(limit: int = 50) -> List[Dict]:
    """
    Fetch latest messages with enhanced retries and validation
    Returns a list of validated message dictionaries
    """
    if not DISCORD_BOT_TOKEN or not CHANNEL_ID:
        logger.error("Missing Discord configuration")
        return []

    messages = []
    retry_attempts = 3
    retry_delay = 1  # seconds between retries

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

def store_message(message: Dict) -> Optional[int]:
    """
    Store message in PostgreSQL with enhanced validation and event publishing
    Returns the stored message ID if successful
    """
    # Validate message structure and content
    if not validate_message(message):
        logger.error(f"Invalid message format: {message}")
        return None

    # Validate message content is not empty
    if not message.get('content', '').strip():
        logger.warning("Skipping empty message")
        return None

    try:
        discord_message = DiscordMessageModel(
            message_id=message['id'],
            content=message['content'],
            author=message['author'],
            author_id=message.get('author_id', ''),
            channel_id=message.get('channel_id', ''),
            timestamp=datetime.fromisoformat(message['timestamp'])
        )

        db.session.add(discord_message)
        db.session.commit()

        # Publish event for other slices to consume
        publish_event(EventType.MESSAGE_STORED, {
            'discord_message_id': discord_message.id,
            'content': message['content'],
            'timestamp': message['timestamp'],
            'source': 'discord'
        })

        return discord_message.id

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error storing message: {e}")
        return None

async def fetch_and_store_messages(limit: int = 50) -> int:
    """Main function to fetch and store messages"""
    messages = await fetch_latest_messages(limit)
    stored_count = 0

    for message in messages:
        if store_message(message):
            stored_count += 1

    return stored_count