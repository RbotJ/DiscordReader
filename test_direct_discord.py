"""
Discord Direct Test

This script directly tests the Discord integration by sending a test message.
"""
import os
import logging
from discord import Client, Intents

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get Discord token and channel ID from environment
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
DISCORD_TEST_CHANNEL = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')

async def send_message(client, channel_id, message):
    """Send a message to a Discord channel."""
    channel = client.get_channel(int(channel_id))
    if channel:
        await channel.send(message)
        logger.info(f"Message sent to channel {channel_id}")
    else:
        logger.error(f"Channel not found: {channel_id}")

class TestClient(Client):
    """Test Discord client for sending messages."""
    
    async def on_ready(self):
        """Called when the client is ready."""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        
        if DISCORD_TEST_CHANNEL:
            try:
                await send_message(
                    self, 
                    int(DISCORD_TEST_CHANNEL), 
                    "🚀 **Test Message**: This is a direct test from the A+ Trading Bot"
                )
            except Exception as e:
                logger.error(f"Error sending message: {e}")
        else:
            logger.error("Test channel ID not configured")
        
        # Close the connection after sending the message
        await self.close()

def main():
    """Run the Discord test."""
    if not DISCORD_BOT_TOKEN:
        logger.error("Discord bot token not found in environment")
        return
    
    if not DISCORD_TEST_CHANNEL:
        logger.error("Discord test channel ID not found in environment")
        return
    
    # Create and run the client
    intents = Intents.default()
    intents.message_content = True
    client = TestClient(intents=intents)
    
    logger.info("Starting Discord client...")
    try:
        client.run(DISCORD_BOT_TOKEN)
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Error running Discord client: {e}")

if __name__ == "__main__":
    main()