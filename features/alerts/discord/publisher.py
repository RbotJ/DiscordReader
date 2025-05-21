"""
Discord Alert Publisher

This module handles publishing alerts to Discord channels based on
trading signals and events from the PostgreSQL event system.
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import discord
from discord.ext import commands

from common.events import subscribe_to_events, publish_event, EventChannels
from common.db_models import NotificationModel
from common.db import db

# Configure logging
logger = logging.getLogger(__name__)

class AlertTypes:
    """Standard alert types for the application"""
    BREAKOUT = "breakout_alert"
    BREAKDOWN = "breakdown_alert"
    REJECTION = "rejection_alert"
    BOUNCE = "bounce_alert"
    SIGNAL_TRIGGERED = "signal_alert"
    TRADE_EXECUTED = "trade_alert"
    POSITION_UPDATE = "position_alert"
    BIAS_FLIP = "bias_flip_alert"
    PRICE_TARGET = "price_target_alert"
    ERROR = "error_alert"

    @classmethod
    def all_types(cls) -> List[str]:
        """Get all alert types as a list"""
        return [
            cls.BREAKOUT, cls.BREAKDOWN, cls.REJECTION, cls.BOUNCE,
            cls.SIGNAL_TRIGGERED, cls.TRADE_EXECUTED, cls.POSITION_UPDATE,
            cls.BIAS_FLIP, cls.PRICE_TARGET, cls.ERROR
        ]

class AlertPublisher:
    """Handles publishing alerts to Discord channels"""

    def __init__(self, bot: commands.Bot):
        """Initialize the alert publisher"""
        self.bot = bot
        self._running = False

        # Map event channels to alert types
        self.channel_mapping = {
            EventChannels.SIGNAL_TRIGGERED: AlertTypes.SIGNAL_TRIGGERED,
            EventChannels.TRADE_EXECUTED: AlertTypes.TRADE_EXECUTED,
            EventChannels.POSITION_UPDATED: AlertTypes.POSITION_UPDATE,
            'error': AlertTypes.ERROR
        }

        if not hasattr(bot, 'channel_manager'):
            logger.error("Channel manager not available")

    def start(self):
        """Start the alert publisher"""
        if self._running:
            logger.warning("Alert publisher is already running")
            return False

        # Subscribe to events
        for channel in self.channel_mapping.keys():
            logger.info(f"Subscribing to event channel: {channel}")
            subscribe_to_events(channel, self._handle_event)

        self._running = True
        logger.info("Alert publisher started")
        return True

    def stop(self):
        """Stop the alert publisher"""
        if not self._running:
            logger.warning("Alert publisher is not running")
            return False

        self._running = False
        logger.info("Alert publisher stopped")
        return True

    async def _handle_event(self, self, data: Dict[str, Any]):
        """Handle an event from PostgreSQL"""
        try:
            event_type = data.get('event_type', '')
            alert_type = self.channel_mapping.get(event_type)

            if not alert_type:
                logger.warning(f"No alert type mapping for event: {event_type}")
                return

            # Create and store notification
            notification = NotificationModel(
                type=alert_type,
                title=self._get_alert_title(alert_type, data),
                message=json.dumps(data),
                meta_data=data
            )

            try:
                db.session.add(notification)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error storing notification: {e}")
                db.session.rollback()
                return

            # Create and publish alert
            alert_data = self._create_alert_data(alert_type, data)
            await self.publish_alert(alert_type, alert_data)

        except Exception as e:
            logger.error(f"Error handling event: {e}")

    def _create_alert_data(self, alert_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert data from event data"""
        alert_data = {
            "type": alert_type,
            "timestamp": datetime.now().isoformat(),
            "source_event": event_data
        }

        if alert_type == AlertTypes.SIGNAL_TRIGGERED:
            alert_data.update({
                "symbol": event_data.get('symbol', 'Unknown'),
                "signal_id": event_data.get('signal_id'),
                "category": event_data.get('category', 'Unknown'),
                "trigger_price": event_data.get('trigger_price')
            })

        elif alert_type == AlertTypes.TRADE_EXECUTED:
            alert_data.update({
                "symbol": event_data.get('symbol', 'Unknown'),
                "side": event_data.get('side', 'Unknown'),
                "quantity": event_data.get('quantity'),
                "price": event_data.get('price'),
                "order_id": event_data.get('order_id')
            })

        elif alert_type == AlertTypes.POSITION_UPDATE:
            alert_data.update({
                "symbol": event_data.get('symbol', 'Unknown'),
                "quantity": event_data.get('quantity'),
                "avg_entry_price": event_data.get('avg_entry_price'),
                "current_price": event_data.get('current_price'),
                "unrealized_pl": event_data.get('unrealized_pl'),
                "unrealized_plpc": event_data.get('unrealized_plpc')
            })

        elif alert_type == AlertTypes.ERROR:
            alert_data.update({
                "error_message": event_data.get('message', 'Unknown error'),
                "error_code": event_data.get('code'),
                "component": event_data.get('component', 'Unknown')
            })

        return alert_data

    async def publish_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> bool:
        """
        Publish an alert to the appropriate Discord channel

        Args:
            alert_type: The type of alert
            alert_data: Alert data

        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Get the channel from the channel manager
            if not hasattr(self.bot, 'channel_manager'):
                logger.error("Channel manager not available")
                return False

            channel = self.bot.channel_manager.get_alert_channel(alert_type)
            if not channel:
                logger.warning(f"No channel set for alert type: {alert_type}")
                return False

            # Format the alert message
            embed = self._format_alert_embed(alert_type, alert_data)

            # Send the message
            await channel.send(embed=embed)
            logger.info(f"Published {alert_type} alert to #{channel.name}")
            return True

        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
            return False

    def _format_alert_embed(self, alert_type: str, alert_data: Dict[str, Any]) -> discord.Embed:
        """
        Format an alert as a Discord embed

        Args:
            alert_type: The type of alert
            alert_data: Alert data

        Returns:
            discord.Embed: Formatted embed
        """
        # Default colors by alert type
        colors = {
            AlertTypes.BREAKOUT: discord.Color.green(),
            AlertTypes.BREAKDOWN: discord.Color.red(),
            AlertTypes.REJECTION: discord.Color.orange(),
            AlertTypes.BOUNCE: discord.Color.blue(),
            AlertTypes.SIGNAL_TRIGGERED: discord.Color.gold(),
            AlertTypes.TRADE_EXECUTED: discord.Color.purple(),
            AlertTypes.POSITION_UPDATE: discord.Color.teal(),
            AlertTypes.BIAS_FLIP: discord.Color.magenta(),
            AlertTypes.PRICE_TARGET: discord.Color.green(),
            AlertTypes.ERROR: discord.Color.dark_red()
        }

        # Default color if not found
        color = colors.get(alert_type, discord.Color.default())

        # Create basic embed
        embed = discord.Embed(
            title=self._get_alert_title(alert_type, alert_data),
            color=color,
            timestamp=datetime.now()
        )

        # Add alert-specific fields
        if alert_type == AlertTypes.SIGNAL_TRIGGERED:
            symbol = alert_data.get('symbol', 'Unknown')
            category = alert_data.get('category', 'Unknown')
            price = alert_data.get('trigger_price', 'Unknown')

            embed.add_field(name="Symbol", value=symbol, inline=True)
            embed.add_field(name="Signal", value=category.title(), inline=True)
            embed.add_field(name="Price", value=f"${price}" if price != 'Unknown' else price, inline=True)

            # Add thumbnail if it's a major stock
            if symbol in ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']:
                embed.set_thumbnail(url=f"https://logo.clearbit.com/{symbol}.com")

        elif alert_type == AlertTypes.TRADE_EXECUTED:
            symbol = alert_data.get('symbol', 'Unknown')
            side = alert_data.get('side', 'Unknown').upper()
            quantity = alert_data.get('quantity', 'Unknown')
            price = alert_data.get('price', 'Unknown')

            embed.add_field(name="Symbol", value=symbol, inline=True)
            embed.add_field(name="Side", value=side, inline=True)
            embed.add_field(name="Quantity", value=quantity, inline=True)
            embed.add_field(name="Price", value=f"${price}" if price != 'Unknown' else price, inline=True)

            # Set color based on buy/sell
            if side == 'BUY':
                embed.color = discord.Color.green()
            elif side == 'SELL':
                embed.color = discord.Color.red()

        elif alert_type == AlertTypes.POSITION_UPDATE:
            symbol = alert_data.get('symbol', 'Unknown')
            quantity = alert_data.get('quantity', 'Unknown')
            entry_price = alert_data.get('avg_entry_price', 'Unknown')
            current_price = alert_data.get('current_price', 'Unknown')
            pl = alert_data.get('unrealized_pl', 'Unknown')
            plpc = alert_data.get('unrealized_plpc', 'Unknown')

            embed.add_field(name="Symbol", value=symbol, inline=True)
            embed.add_field(name="Quantity", value=quantity, inline=True)
            embed.add_field(name="Entry Price", value=f"${entry_price}" if entry_price != 'Unknown' else entry_price, inline=True)
            embed.add_field(name="Current Price", value=f"${current_price}" if current_price != 'Unknown' else current_price, inline=True)

            # Format P/L
            if pl != 'Unknown' and plpc != 'Unknown':
                pl_sign = '+' if float(pl) >= 0 else ''
                plpc_sign = '+' if float(plpc) >= 0 else ''
                pl_formatted = f"{pl_sign}${pl:.2f} ({plpc_sign}{plpc:.2f}%)"

                # Set color based on P/L
                if float(pl) > 0:
                    embed.color = discord.Color.green()
                elif float(pl) < 0:
                    embed.color = discord.Color.red()

                embed.add_field(name="Unrealized P/L", value=pl_formatted, inline=True)

        elif alert_type == AlertTypes.ERROR:
            component = alert_data.get('component', 'Unknown')
            message = alert_data.get('error_message', 'Unknown error')
            code = alert_data.get('error_code', 'N/A')

            embed.add_field(name="Component", value=component, inline=True)
            embed.add_field(name="Error Code", value=code, inline=True)
            embed.add_field(name="Message", value=message, inline=False)

        # Add footer with timestamp
        embed.set_footer(text=f"A+ Trading | {alert_type}")

        return embed

    def _get_alert_title(self, alert_type: str, alert_data: Dict[str, Any]) -> str:
        """
        Get the title for an alert embed

        Args:
            alert_type: The type of alert
            alert_data: Alert data

        Returns:
            str: Alert title
        """
        if alert_type == AlertTypes.SIGNAL_TRIGGERED:
            symbol = alert_data.get('symbol', 'Unknown')
            category = alert_data.get('category', 'Unknown').title()
            return f"🔔 Signal Triggered: {category} on {symbol}"

        elif alert_type == AlertTypes.TRADE_EXECUTED:
            symbol = alert_data.get('symbol', 'Unknown')
            side = alert_data.get('side', 'Unknown').upper()
            emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "🔄"
            return f"{emoji} Trade Executed: {side} {symbol}"

        elif alert_type == AlertTypes.POSITION_UPDATE:
            symbol = alert_data.get('symbol', 'Unknown')
            if 'unrealized_pl' in alert_data:
                pl = alert_data.get('unrealized_pl', 0)
                emoji = "📈" if float(pl) >= 0 else "📉"
                return f"{emoji} Position Update: {symbol}"
            else:
                return f"🔄 Position Update: {symbol}"

        elif alert_type == AlertTypes.ERROR:
            return f"⚠️ Error: {alert_data.get('component', 'System')}"

        else:
            # Default title for other alert types
            readable_type = alert_type.replace('_', ' ').title()
            return f"🔔 {readable_type}"

def setup(bot: commands.Bot):
    """
    Set up the alert publisher for the bot

    Args:
        bot: The Discord bot
    """
    # Create alert publisher
    bot.alert_publisher = AlertPublisher(bot)

    # Start on ready
    @bot.event
    async def on_ready():
        if hasattr(bot, 'alert_publisher'):
            bot.alert_publisher.start()
            logger.info("Alert publisher started")

    # Register commands
    register_alert_commands(bot)

def register_alert_commands(bot: commands.Bot):
    """
    Register alert-related commands

    Args:
        bot: The Discord bot
    """
    # Only add if alert_group doesn't already exist
    if not any(cmd.name == "alert" for cmd in bot.tree.get_commands()):
        return

    # The alert command group should be registered by channel_manager.py
    # We'll retrieve it to add additional commands
    alert_group = next((cmd for cmd in bot.tree.get_commands() if cmd.name == "alert"), None)

    if not alert_group:
        logger.warning("Alert command group not found, can't register alert commands")
        return

    @alert_group.command(name="test", description="Send a test alert to a channel")
    @app_commands.describe(
        alert_type="The type of alert to test",
        symbol="The ticker symbol to use in the test alert"
    )
    @app_commands.choices(alert_type=[
        app_commands.Choice(name=alert_type.replace('_', ' ').title(), value=alert_type)
        for alert_type in AlertTypes.all_types()
    ])
    async def test_alert(
        interaction: discord.Interaction,
        alert_type: str,
        symbol: str = "SPY"
    ):
        """Send a test alert to a channel"""
        # Check if user has permissions
        if not interaction.user.guild_permissions.manage_guild and not any(role.name == "Admin" for role in interaction.user.roles):
            await interaction.response.send_message("❌ You need 'Manage Server' permission or 'Admin' role to use this command.", ephemeral=True)
            return

        # Check if the alert type has a channel configured
        if not hasattr(bot, 'channel_manager'):
            await interaction.response.send_message("❌ Channel manager not available.", ephemeral=True)
            return

        channel = bot.channel_manager.get_alert_channel(alert_type)
        if not channel:
            await interaction.response.send_message(f"❌ No channel configured for alert type '{alert_type}'. Use `/alert set_channel` first.", ephemeral=True)
            return

        # Create test alert data
        test_data = {
            "type": alert_type,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }

        # Add type-specific test data
        if alert_type == AlertTypes.SIGNAL_TRIGGERED:
            test_data.update({
                "signal_id": 12345,
                "category": "breakout",
                "trigger_price": 450.75
            })
        elif alert_type == AlertTypes.TRADE_EXECUTED:
            test_data.update({
                "side": "buy",
                "quantity": 10,
                "price": 451.25,
                "order_id": "test-order-123"
            })
        elif alert_type == AlertTypes.POSITION_UPDATE:
            test_data.update({
                "quantity": 10,
                "avg_entry_price": 450.0,
                "current_price": 455.0,
                "unrealized_pl": 50.0,
                "unrealized_plpc": 0.0111  # 1.11%
            })
        elif alert_type == AlertTypes.ERROR:
            test_data.update({
                "component": "Trading Engine",
                "error_message": "This is a test error message",
                "error_code": "TEST-001"
            })

        # Send the test alert
        if hasattr(bot, 'alert_publisher'):
            success = await bot.alert_publisher.publish_alert(alert_type, test_data)

            if success:
                await interaction.response.send_message(f"✅ Test alert sent to #{channel.name}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to send test alert", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Alert publisher not available", ephemeral=True)
    async def test_alert(self, alert_type: str, test_data: Optional[Dict] = None) -> bool:
        """
        Send a test alert to verify the system
        
        Args:
            alert_type: Type of alert to test
            test_data: Optional test data, uses defaults if None
            
        Returns:
            bool: True if alert was sent successfully
        """
        if not test_data:
            test_data = {
                'symbol': 'TEST',
                'price': 100.00,
                'timestamp': datetime.now().isoformat()
            }
            
        return await self.publish_alert(alert_type, test_data)
