import os
import asyncio
import logging
from datetime import datetime
import discord
from common.events import publish_event, EventChannels
from common.db import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SetupMessageClient(discord.Client):
    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')

    async def on_message(self, message):
        if message.author == self.user:
            return

        try:
            # Store message in database
            event_data = {
                'event_type': 'discord_message',
                'message_id': str(message.id),
                'content': message.content,
                'author': str(message.author),
                'timestamp': message.created_at.isoformat()
            }

            # Publish event
            publish_event(EventChannels.DISCORD_MESSAGE_RECEIVED, event_data)

            logger.info(f"Message stored and published: {message.id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

async def main():
    # Get Discord token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("No Discord bot token found")
        return

    # Create client
    intents = discord.Intents.default()
    intents.message_content = True
    client = SetupMessageClient(intents=intents)

    try:
        await client.start(token)
    except Exception as e:
        logger.error(f"Error running Discord client: {e}")
    finally:
        await client.close()

if __name__ == '__main__':
    asyncio.run(main())