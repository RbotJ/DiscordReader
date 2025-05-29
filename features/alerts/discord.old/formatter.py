"""
Discord Alert Formatter

This module handles formatting different types of alerts for Discord messages,
ensuring consistent and visually appealing notification styles.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple
import discord

from features.alerts.discord.publisher import AlertTypes

# Configure logging
logger = logging.getLogger(__name__)

class AlertFormatter:
    """Formats alerts for Discord messages"""
    
    @staticmethod
    def format_signal_alert(data: Dict[str, Any]) -> Tuple[str, Optional[discord.Embed]]:
        """
        Format a signal alert
        
        Args:
            data: Signal data
            
        Returns:
            Tuple[str, Optional[discord.Embed]]: Message content and embed
        """
        symbol = data.get('symbol', 'Unknown')
        category = data.get('category', 'Unknown').title()
        price = data.get('trigger_price', 'Unknown')
        
        # Determine color and emoji based on signal category
        color = discord.Color.default()
        emoji = "🚨"
        
        if category.lower() == 'breakout':
            color = discord.Color.green()
            emoji = "🚀"
        elif category.lower() == 'breakdown':
            color = discord.Color.red()
            emoji = "📉"
        elif category.lower() == 'rejection':
            color = discord.Color.orange()
            emoji = "🛑"
        elif category.lower() == 'bounce':
            color = discord.Color.blue()
            emoji = "🔄"
        
        # Create message content (visible in notifications)
        content = f"{emoji} **{category} Signal on {symbol}** at ${price}"
        
        # Create embed
        embed = discord.Embed(
            title=f"{emoji} {category} Signal",
            description=f"A {category.lower()} signal has been triggered for {symbol}",
            color=color,
            timestamp=datetime.now()
        )
        
        # Add fields
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Price", value=f"${price}" if price != 'Unknown' else price, inline=True)
        
        # Add thumbnail if it's a major stock
        if symbol in ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']:
            embed.set_thumbnail(url=f"https://logo.clearbit.com/{symbol}.com")
        
        # Add footer
        embed.set_footer(text="A+ Trading | Signal Alert")
        
        return content, embed
    
    @staticmethod
    def format_trade_alert(data: Dict[str, Any]) -> Tuple[str, Optional[discord.Embed]]:
        """
        Format a trade execution alert
        
        Args:
            data: Trade data
            
        Returns:
            Tuple[str, Optional[discord.Embed]]: Message content and embed
        """
        symbol = data.get('symbol', 'Unknown')
        side = data.get('side', 'Unknown').upper()
        quantity = data.get('quantity', 'Unknown')
        price = data.get('price', 'Unknown')
        
        # Determine color and emoji based on trade side
        color = discord.Color.default()
        emoji = "🔄"
        
        if side.lower() == 'buy':
            color = discord.Color.green()
            emoji = "🟢"
        elif side.lower() == 'sell':
            color = discord.Color.red()
            emoji = "🔴"
        
        # Create message content (visible in notifications)
        content = f"{emoji} **{side} {quantity} {symbol}** at ${price}"
        
        # Create embed
        embed = discord.Embed(
            title=f"{emoji} Trade Executed: {side} {symbol}",
            description=f"A trade has been executed for {symbol}",
            color=color,
            timestamp=datetime.now()
        )
        
        # Add fields
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Side", value=side, inline=True)
        embed.add_field(name="Quantity", value=quantity, inline=True)
        embed.add_field(name="Price", value=f"${price}" if price != 'Unknown' else price, inline=True)
        
        # Add relevant emojis based on trade side
        if side.lower() == 'buy':
            embed.add_field(name="Action", value="◀️ ENTRY", inline=True)
        elif side.lower() == 'sell':
            embed.add_field(name="Action", value="EXIT ▶️", inline=True)
        
        # Add thumbnail
        if symbol in ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']:
            embed.set_thumbnail(url=f"https://logo.clearbit.com/{symbol}.com")
        
        # Add footer
        embed.set_footer(text="A+ Trading | Trade Alert")
        
        return content, embed
    
    @staticmethod
    def format_position_alert(data: Dict[str, Any]) -> Tuple[str, Optional[discord.Embed]]:
        """
        Format a position update alert
        
        Args:
            data: Position data
            
        Returns:
            Tuple[str, Optional[discord.Embed]]: Message content and embed
        """
        symbol = data.get('symbol', 'Unknown')
        quantity = data.get('quantity', 'Unknown')
        entry_price = data.get('avg_entry_price', 'Unknown')
        current_price = data.get('current_price', 'Unknown')
        pl = data.get('unrealized_pl', 'Unknown')
        plpc = data.get('unrealized_plpc', 'Unknown')
        
        # Determine color and emoji based on P/L
        color = discord.Color.light_grey()
        emoji = "🔄"
        
        if pl != 'Unknown' and float(pl) > 0:
            color = discord.Color.green()
            emoji = "📈"
        elif pl != 'Unknown' and float(pl) < 0:
            color = discord.Color.red()
            emoji = "📉"
        
        # Format P/L
        pl_formatted = "Unknown"
        if pl != 'Unknown' and plpc != 'Unknown':
            pl_sign = '+' if float(pl) >= 0 else ''
            plpc_sign = '+' if float(plpc) >= 0 else ''
            pl_formatted = f"{pl_sign}${pl:.2f} ({plpc_sign}{plpc:.2f}%)"
        
        # Create message content (visible in notifications)
        content = f"{emoji} **Position Update: {symbol}** - {pl_formatted}"
        
        # Create embed
        embed = discord.Embed(
            title=f"{emoji} Position Update: {symbol}",
            description=f"Position updated for {symbol}",
            color=color,
            timestamp=datetime.now()
        )
        
        # Add fields
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Quantity", value=quantity, inline=True)
        embed.add_field(name="Entry Price", value=f"${entry_price}" if entry_price != 'Unknown' else entry_price, inline=True)
        embed.add_field(name="Current Price", value=f"${current_price}" if current_price != 'Unknown' else current_price, inline=True)
        embed.add_field(name="Unrealized P/L", value=pl_formatted, inline=True)
        
        # Add thumbnail
        if symbol in ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']:
            embed.set_thumbnail(url=f"https://logo.clearbit.com/{symbol}.com")
        
        # Add footer
        embed.set_footer(text="A+ Trading | Position Alert")
        
        return content, embed
    
    @staticmethod
    def format_error_alert(data: Dict[str, Any]) -> Tuple[str, Optional[discord.Embed]]:
        """
        Format an error alert
        
        Args:
            data: Error data
            
        Returns:
            Tuple[str, Optional[discord.Embed]]: Message content and embed
        """
        component = data.get('component', 'Unknown')
        message = data.get('error_message', 'Unknown error')
        code = data.get('error_code', 'N/A')
        
        # Create message content (visible in notifications)
        content = f"⚠️ **System Error: {component}** - {code}"
        
        # Create embed
        embed = discord.Embed(
            title=f"⚠️ Error: {component}",
            description=message,
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        
        # Add fields
        embed.add_field(name="Component", value=component, inline=True)
        embed.add_field(name="Error Code", value=code, inline=True)
        
        # Add footer
        embed.set_footer(text="A+ Trading | Error Alert")
        
        return content, embed
    
    @staticmethod
    def format_alert(alert_type: str, data: Dict[str, Any]) -> Tuple[str, Optional[discord.Embed]]:
        """
        Format an alert based on its type
        
        Args:
            alert_type: The type of alert
            data: Alert data
            
        Returns:
            Tuple[str, Optional[discord.Embed]]: Message content and embed
        """
        try:
            if alert_type == AlertTypes.SIGNAL_TRIGGERED:
                return AlertFormatter.format_signal_alert(data)
            elif alert_type == AlertTypes.TRADE_EXECUTED:
                return AlertFormatter.format_trade_alert(data)
            elif alert_type == AlertTypes.POSITION_UPDATE:
                return AlertFormatter.format_position_alert(data)
            elif alert_type == AlertTypes.ERROR:
                return AlertFormatter.format_error_alert(data)
            else:
                # Default generic format for other alert types
                title = alert_type.replace('_', ' ').title()
                content = f"🔔 **{title}**"
                embed = discord.Embed(
                    title=f"🔔 {title}",
                    description=f"Alert of type {alert_type}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                return content, embed
        except Exception as e:
            logger.error(f"Error formatting alert: {e}")
            # Return generic error message
            return f"⚠️ **Alert: {alert_type}**", None