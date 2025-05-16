"""
Discord Commands Module

This module processes commands received through Discord messages.
"""
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import discord
from flask import current_app

from features.discord.client import register_message_handler, send_bot_message
from app import db
from common.db_models import SetupModel, TickerSetupModel, SignalModel, MarketDataModel

logger = logging.getLogger(__name__)

# Command prefix
CMD_PREFIX = "!aplus"

# Command handler registry
command_handlers = {}

def command(name: str, description: str):
    """
    Decorator to register a command handler.
    
    Args:
        name: Command name
        description: Command description
    """
    def decorator(f):
        command_handlers[name] = {
            'handler': f,
            'description': description
        }
        return f
    return decorator

def handle_discord_message(message: discord.Message):
    """
    Process a Discord message and route to appropriate command handler.
    
    Args:
        message: The Discord message
    """
    # Check if message starts with the command prefix
    if not message.content.startswith(CMD_PREFIX):
        return
        
    # Extract command and arguments
    parts = message.content[len(CMD_PREFIX):].strip().split(' ', 1)
    cmd = parts[0].lower() if parts else ''
    args = parts[1] if len(parts) > 1 else ''
    
    # Process command
    if cmd in command_handlers:
        try:
            logger.info(f"Processing Discord command: {cmd}")
            command_handlers[cmd]['handler'](message, args)
        except Exception as e:
            logger.exception(f"Error processing command '{cmd}': {e}")
            reply = f"Error processing command: {str(e)}"
            send_bot_message(reply)
    elif cmd:
        # Unknown command
        send_bot_message(f"Unknown command: '{cmd}'. Use `{CMD_PREFIX} help` for available commands.")

@command('help', 'Display available commands')
def cmd_help(message: discord.Message, args: str):
    """
    Display help information about available commands.
    
    Args:
        message: Discord message
        args: Command arguments
    """
    help_text = "**Available Commands:**\n\n"
    
    for name, info in sorted(command_handlers.items()):
        help_text += f"`{CMD_PREFIX} {name}` - {info['description']}\n"
    
    send_bot_message(help_text)

@command('status', 'Show system status')
def cmd_status(message: discord.Message, args: str):
    """
    Display system status.
    
    Args:
        message: Discord message
        args: Command arguments
    """
    with current_app.app_context():
        # Count database records
        setup_count = db.session.query(SetupModel).count()
        ticker_count = db.session.query(TickerSetupModel).count()
        signal_count = db.session.query(SignalModel).count()
        market_data_count = db.session.query(MarketDataModel).count()
        
        # Format status message
        status = f"**A+ Trading System Status**\n\n"
        status += f"Database Records:\n"
        status += f"- Setup Messages: {setup_count}\n"
        status += f"- Ticker Setups: {ticker_count}\n"
        status += f"- Trading Signals: {signal_count}\n"
        status += f"- Market Data Points: {market_data_count}\n\n"
        
        # Add timestamp
        status += f"_Status as of {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC_"
        
        send_bot_message(status)

@command('latest', 'Show latest trading setups')
def cmd_latest(message: discord.Message, args: str):
    """
    Display latest trading setups.
    
    Args:
        message: Discord message
        args: Command arguments
    """
    with current_app.app_context():
        # Get the 5 most recent setup messages
        setups = SetupModel.query.order_by(SetupModel.created_at.desc()).limit(5).all()
        
        if not setups:
            send_bot_message("No trading setups found in the database.")
            return
            
        reply = "**Latest Trading Setups**\n\n"
        
        for setup in setups:
            # Get tickers for this setup
            ticker_symbols = [ts.symbol for ts in setup.ticker_setups]
            
            reply += f"**{setup.date.strftime('%Y-%m-%d')}** ({setup.source})\n"
            reply += f"- ID: {setup.id}\n"
            reply += f"- Tickers: {', '.join(ticker_symbols[:10])}"
            
            if len(ticker_symbols) > 10:
                reply += f" and {len(ticker_symbols) - 10} more"
                
            reply += f"\n- Added: {setup.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        
        send_bot_message(reply)

@command('ticker', 'Show trading signals for a ticker')
def cmd_ticker(message: discord.Message, args: str):
    """
    Display trading signals for a specific ticker.
    
    Args:
        message: Discord message
        args: Command arguments
    """
    if not args:
        send_bot_message("Please specify a ticker symbol. Example: `!aplus ticker SPY`")
        return
        
    # Extract ticker symbol
    symbol = args.split()[0].upper()
    
    with current_app.app_context():
        # Get the latest ticker setup for this symbol
        ticker_setup = (TickerSetupModel.query
                       .filter_by(symbol=symbol)
                       .order_by(TickerSetupModel.created_at.desc())
                       .first())
        
        if not ticker_setup:
            send_bot_message(f"No trading signals found for {symbol}.")
            return
            
        # Get the parent setup
        setup = SetupModel.query.get(ticker_setup.setup_id)
        
        # Get signals
        signals = SignalModel.query.filter_by(ticker_setup_id=ticker_setup.id).all()
        
        # Format response
        reply = f"**Trading Signals for {symbol}**\n\n"
        reply += f"From setup on {setup.date.strftime('%Y-%m-%d')}:\n\n"
        
        for signal in signals:
            # Format trigger value
            trigger_val = signal.trigger_value
            if isinstance(trigger_val, list):
                trigger_str = f"{min(trigger_val)}-{max(trigger_val)}"
            else:
                trigger_str = str(trigger_val)
                
            # Format targets
            targets = signal.targets
            targets_str = ", ".join([str(t) for t in targets])
            
            reply += f"**{signal.category.capitalize()}** ({signal.comparison}) {trigger_str}\n"
            reply += f"- Aggressiveness: {signal.aggressiveness}\n"
            reply += f"- Targets: {targets_str}\n"
            
            if signal.triggered_at:
                reply += f"- Triggered: {signal.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
            reply += "\n"
        
        # Add bias if available
        if ticker_setup.bias:
            bias = ticker_setup.bias
            reply += f"**Market Bias**: {bias.direction.capitalize()} {bias.condition} {bias.price}\n"
            
            if bias.flip_direction and bias.flip_price_level:
                reply += f"- Flips {bias.flip_direction} below {bias.flip_price_level}\n"
        
        send_bot_message(reply)

def register_command_handlers():
    """Register Discord command message handler."""
    register_message_handler(handle_discord_message)
    logger.info("Registered Discord command handlers")