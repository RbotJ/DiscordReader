#!/usr/bin/env python3
"""
Discord Test Script for A+ Channel Access

This script tests accessing the A+ channel with the new bot token.
"""
import os
import asyncio
import discord
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get Discord config
TOKEN = os.environ.get('DISCORD_BOT_TOKEN_APLUS')
CHANNEL_ID = 1372012942848954388

async def main():
    """Test Discord channel access with the new bot token."""
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN_APLUS environment variable not set")
        return
        
    # Create client with message content intent
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
        
        try:
            # Try to get the channel
            logger.info(f"Attempting to access channel ID: {CHANNEL_ID}")
            
            try:
                channel = client.get_channel(CHANNEL_ID)
                if channel:
                    logger.info(f"Found channel in cache: {channel.name}")
                else:
                    logger.info(f"Channel not in cache, trying to fetch it")
                    channel = await client.fetch_channel(CHANNEL_ID)
                    logger.info(f"Successfully fetched channel: {channel.name}")
            except Exception as e:
                logger.error(f"Error accessing channel: {e}")
                await client.close()
                return
                
            # Try to get messages
            logger.info(f"Attempting to fetch messages from channel")
            try:
                messages = []
                async for msg in channel.history(limit=3):
                    logger.info(f"Message {msg.id} from {msg.author}: {msg.content[:50]}...")
                    messages.append(msg)
                    
                logger.info(f"Successfully fetched {len(messages)} messages")
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            # Always disconnect when done
            await client.close()
    
    try:
        await client.start(TOKEN)
    except KeyboardInterrupt:
        await client.close()
    except Exception as e:
        logger.error(f"Error starting client: {e}")

if __name__ == "__main__":
    asyncio.run(main())