import asyncio
import logging
from datetime import datetime
import discord
from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import DiscordMessageModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_discord_connection(token, channel_id):
    """Test Discord connection and message storage"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            channel = client.get_channel(int(channel_id))
            async for message in channel.history(limit=1):
                # Store message in database
                db_message = DiscordMessageModel(
                    message_id=str(message.id),
                    content=message.content,
                    author=str(message.author),
                    timestamp=message.created_at,
                    channel_id=str(channel_id)
                )
                db.session.add(db_message)
                db.session.commit()

                # Publish event
                publish_event(EventChannels.DISCORD_SETUP_MESSAGE, {
                    "message_id": str(message.id),
                    "content": message.content
                })

                logger.info(f"Stored and published message: {message.id}")

        except Exception as e:
            logger.error(f"Error processing Discord message: {e}")
        finally:
            await client.close()

    await client.start(token)

if __name__ == "__main__":
    import os
    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    asyncio.run(test_discord_connection(token, channel_id))