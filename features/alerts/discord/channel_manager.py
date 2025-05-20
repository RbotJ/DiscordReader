"""
Discord Channel Manager

This module handles the discovery, caching, and configuration of Discord channels
for the alerts system. It provides functionality to:
1. Discover and cache text channels on startup
2. Load and save alert channel configurations
3. Map alert types to specific Discord channels
"""

import os
import json
import logging
from typing import Dict, Optional, List, Any
import discord
from discord import app_commands
from discord.ext import commands

# Configure logging
logger = logging.getLogger(__name__)

class ChannelManager:
    """Manages Discord channel discovery and configuration for alerts"""
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the channel manager
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.text_channels: Dict[str, int] = {}  # Maps channel name -> ID
        self.alert_config: Dict[str, int] = {}   # Maps alert type -> channel ID
        self.config_path = os.path.join('config', 'alert_channels.json')
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
    
    async def discover_channels(self):
        """
        Discover and cache all text channels across all guilds the bot is in
        
        Returns:
            Dict[str, int]: A mapping of channel names to their IDs
        """
        self.text_channels = {}
        
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                # Use channel name as key, store channel ID as value
                self.text_channels[channel.name] = channel.id
                
        logger.info(f"Discovered {len(self.text_channels)} text channels: {self.text_channels}")
        return self.text_channels
    
    def load_alert_config(self) -> Dict[str, int]:
        """
        Load alert channel configuration from disk
        
        Returns:
            Dict[str, int]: The loaded configuration
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.alert_config = json.load(f)
                logger.info(f"Loaded alert configuration: {self.alert_config}")
            else:
                self.alert_config = {}
                logger.info("ℹ️ No alert channels yet — use `/set_alert_channel` to configure.")
                
            return self.alert_config
            
        except Exception as e:
            logger.error(f"Error loading alert configuration: {e}")
            self.alert_config = {}
            return self.alert_config
    
    def save_alert_config(self) -> bool:
        """
        Save alert channel configuration to disk
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.alert_config, f, indent=2)
            logger.info(f"Saved alert configuration: {self.alert_config}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving alert configuration: {e}")
            return False
    
    def set_alert_channel(self, alert_type: str, channel_id: int) -> bool:
        """
        Set a channel for a specific alert type
        
        Args:
            alert_type: The type of alert (e.g., "breakout_alert")
            channel_id: The Discord channel ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.alert_config[alert_type] = channel_id
            success = self.save_alert_config()
            return success
        except Exception as e:
            logger.error(f"Error setting alert channel: {e}")
            return False
    
    def get_alert_channel(self, alert_type: str) -> Optional[discord.TextChannel]:
        """
        Get the channel for a specific alert type
        
        Args:
            alert_type: The type of alert (e.g., "breakout_alert")
            
        Returns:
            Optional[discord.TextChannel]: The Discord channel or None if not found
        """
        try:
            channel_id = self.alert_config.get(alert_type)
            if not channel_id:
                logger.warning(f"No channel set for alert type: {alert_type}")
                return None
                
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel with ID {channel_id} for alert type {alert_type} not found")
                return None
                
            return channel
            
        except Exception as e:
            logger.error(f"Error getting alert channel: {e}")
            return None

def setup(bot: commands.Bot):
    """
    Set up channel management for the bot
    
    Args:
        bot: The Discord bot
    """
    # Create channel manager
    bot.channel_manager = ChannelManager(bot)
    
    # Register slash command setup
    register_channel_commands(bot)
    
    # Register event handlers
    @bot.event
    async def on_ready():
        logger.info(f"{bot.user.name} is ready. Discovering channels...")
        await bot.channel_manager.discover_channels()
        bot.channel_manager.load_alert_config()
        
        # Check if alert config is empty
        if not bot.channel_manager.alert_config:
            logger.info("ℹ️ No alert channels yet — use `/set_alert_channel` to configure.")

def register_channel_commands(bot: commands.Bot):
    """
    Register channel-related slash commands
    
    Args:
        bot: The Discord bot
    """
    # Create a command group for alert management
    alert_group = app_commands.Group(name="alert", description="Commands for managing alerts")
    
    @alert_group.command(name="set_channel", description="Set a channel for a specific alert type")
    @app_commands.describe(
        alert_type="The type of alert (e.g., breakout_alert, rejection_alert)",
        channel="The channel to send alerts to"
    )
    async def set_alert_channel(
        interaction: discord.Interaction, 
        alert_type: str, 
        channel: discord.TextChannel
    ):
        """Set a channel for a specific alert type"""
        # Check if user has permissions
        if not interaction.user.guild_permissions.manage_guild and not any(role.name == "Admin" for role in interaction.user.roles):
            await interaction.response.send_message("❌ You need 'Manage Server' permission or 'Admin' role to use this command.", ephemeral=True)
            return
        
        # Set the alert channel
        success = bot.channel_manager.set_alert_channel(alert_type, channel.id)
        
        if success:
            await interaction.response.send_message(
                f"✅ Alert type '{alert_type}' will now post in #{channel.name}.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to set alert channel for '{alert_type}'.",
                ephemeral=True
            )
    
    @alert_group.command(name="list_channels", description="List all configured alert channels")
    async def list_alert_channels(interaction: discord.Interaction):
        """List all configured alert channels"""
        # Check if user has permissions
        if not interaction.user.guild_permissions.manage_guild and not any(role.name == "Admin" for role in interaction.user.roles):
            await interaction.response.send_message("❌ You need 'Manage Server' permission or 'Admin' role to use this command.", ephemeral=True)
            return
        
        alert_config = bot.channel_manager.alert_config
        
        if not alert_config:
            await interaction.response.send_message("No alert channels configured yet.", ephemeral=True)
            return
        
        # Format the response
        response = "📢 **Configured Alert Channels**\n\n"
        for alert_type, channel_id in alert_config.items():
            channel = bot.get_channel(channel_id)
            channel_name = channel.name if channel else f"Unknown (ID: {channel_id})"
            response += f"• **{alert_type}**: #{channel_name}\n"
        
        await interaction.response.send_message(response, ephemeral=True)
    
    # Add the alert commands group to the bot
    bot.tree.add_command(alert_group)