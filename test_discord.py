#!/usr/bin/env python3
"""
Simple Discord bot test to verify token and connection
"""
import os
import discord
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"→ test_discord.py at {__file__}")

# Check if token exists
token = os.environ.get('DISCORD_BOT_TOKEN')
print(f"Discord token: {'Found' if token else 'Missing'}")

if not token:
    print("❌ No Discord token found - please check your secrets")
    exit(1)

# Create minimal bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Discord bot connected as {bot.user}")
    
    if bot.guilds:
        guild = bot.guilds[0]
        print(f"📡 Connected to guild: {guild.name}")
        
        # Look for our target channel
        target_name = "aplus-setups"
        from discord.utils import get
        channel = get(guild.text_channels, name=target_name)
        
        if channel:
            print(f"🎯 Found target channel: #{channel.name} ({channel.id})")
        else:
            print(f"❌ Could not find channel '{target_name}'")
            print(f"Available channels: {[ch.name for ch in guild.text_channels]}")
    else:
        print("❌ Bot is not connected to any guilds")

# Run the bot
print("🚀 Starting Discord bot test...")
try:
    bot.run(token)
except Exception as e:
    print(f"❌ Bot failed to start: {e}")