import discord
import logging
from datetime import datetime
from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import DiscordChannelModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestDiscordClient(discord.Client):
    async def test_channel(self, channel_id):
        try:
            channel = self.get_channel(int(channel_id))
            if not channel:
                logger.error("Channel not found")
                return False

            # Store channel info
            db_channel = DiscordChannelModel(
                channel_id=str(channel_id),
                name=channel.name,
                created_at=datetime.utcnow()
            )
            db.session.add(db_channel)
            db.session.commit()

            logger.info(f"Successfully tested channel: {channel.name}")
            return True

        except Exception as e:
            logger.error(f"Channel test failed: {e}")
            return False

async def run_test(token, channel_id):
    client = TestDiscordClient(intents=discord.Intents.default())
    await client.start(token)
    await client.test_channel(channel_id)
    await client.close()

if __name__ == "__main__":
    import os
    import asyncio
    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    asyncio.run(run_test(token, channel_id))