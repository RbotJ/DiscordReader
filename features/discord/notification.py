"""
Discord Notification System

This module provides functionality for sending notifications to Discord channels
about trade setups, signals, and system status.
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from features.discord.client import (
    send_status_update, send_trade_alert, send_error_notification,
    send_test_message, is_discord_available
)
from features.setups.models import (
    SetupMessage, TickerSetup, Signal, Bias
)

logger = logging.getLogger(__name__)

from common.events import publish_event, get_latest_events
from common.event_constants import EventChannels
from common.db import db

def format_signal_notification(signal: Signal) -> str:
    """
    Format a signal notification message.

    Args:
        signal: Signal object to format

    Returns:
        Formatted message
    """
    # Extract signal details
    symbol = signal.ticker_setup.symbol
    category = signal.category

    # Format trigger value based on JSON structure
    trigger_display = ""
    if isinstance(signal.trigger_value, dict):
        if signal.trigger_value.get('type') == 'single':
            trigger_display = f"{signal.trigger_value.get('value')}"
        elif signal.trigger_value.get('type') == 'range':
            trigger_display = f"{signal.trigger_value.get('low')} - {signal.trigger_value.get('high')}"

    # Format targets
    targets_display = ""
    if isinstance(signal.targets, list) and signal.targets:
        targets_display = ", ".join([str(t) for t in signal.targets])

    # Create message
    message = f"**{symbol} {category.title()} Signal**\n"
    message += f"• Trigger: {trigger_display}\n"

    if targets_display:
        message += f"• Targets: {targets_display}\n"

    # Add bias information if available
    bias = get_bias_for_ticker_setup(signal.ticker_setup_id)
    if bias:
        bias_direction = bias.direction.lower()
        price = bias.price
        message += f"• Bias: {bias_direction.title()} {bias.condition} {price}\n"

        # Add flip information if available
        if hasattr(bias, 'bias_flip') and bias.bias_flip:
            message += f"• Flip to {bias.bias_flip.direction.value.title()} below {bias.bias_flip.price_level}\n"

    return message

def get_bias_for_ticker_setup(ticker_setup_id: int) -> Optional[Bias]:
    """
    Get bias for a ticker setup.

    Args:
        ticker_setup_id: ID of the ticker setup

    Returns:
        Bias object if found, None otherwise
    """
    try:
        return Bias.query.filter_by(ticker_setup_id=ticker_setup_id).first()
    except Exception as e:
        logger.error(f"Error getting bias for ticker setup {ticker_setup_id}: {e}")
        return None

def send_signal_notification(signal: Signal, test_mode: bool = False) -> bool:
    """
    Send a notification for a newly detected signal.

    Args:
        signal: The signal to notify about
        test_mode: Whether to send to test channel (default: False)

    Returns:
        Success status
    """
    if not is_discord_available:
        logger.warning("Discord not available, signal notification not sent")
        return False

    try:
        # Format the notification message
        message = format_signal_notification(signal)

        # Send to the appropriate channel
        if test_mode:
            return send_test_message(message)
        else:
            return send_trade_alert(
                symbol=signal.ticker_setup.symbol,
                alert_type=signal.category,
                details=message
            )
    except Exception as e:
        logger.error(f"Error sending signal notification: {e}")
        return False

def notify_new_setup_message(setup_message: SetupMessage, test_mode: bool = False) -> bool:
    """
    Send a notification for a newly received setup message.

    Args:
        setup_message: The setup message that was received
        test_mode: Whether to send to test channel (default: False)

    Returns:
        Success status
    """
    if not is_discord_available:
        logger.warning("Discord not available, setup notification not sent")
        return False

    try:
        # Query directly to ensure we get the proper collection
        ticker_setups = TickerSetup.query.filter_by(setup_id=setup_message.id).all()
        ticker_symbols = [ts.symbol for ts in ticker_setups]

        # Format message
        message = f"**New Trading Setup Received**\n"
        message += f"• Date: {setup_message.date.strftime('%Y-%m-%d')}\n"
        message += f"• Source: {setup_message.source}\n"
        message += f"• Tickers: {', '.join(ticker_symbols)}\n"

        # Count signals
        signal_count = 0
        for ts in ticker_setups:
            signals = Signal.query.filter_by(ticker_setup_id=ts.id).all()
            signal_count += len(signals)

        message += f"• Signals: {signal_count}\n"

        # Send to the appropriate channel
        if test_mode:
            return send_test_message(message)
        else:
            return send_status_update(message)
    except Exception as e:
        logger.error(f"Error sending setup notification: {e}")
        return False

def notify_signal_detected(signal: Signal, test_mode: bool = False) -> bool:
    """
    Send a notification when a signal is detected.

    Args:
        signal: The detected signal
        test_mode: Whether to send to test channel (default: False)

    Returns:
        Success status
    """
    return send_signal_notification(signal, test_mode)

def notify_system_status(status_message: str, test_mode: bool = False) -> bool:
    """
    Send a system status notification.

    Args:
        status_message: Status message
        test_mode: Whether to send to test channel (default: False)

    Returns:
        Success status
    """
    if not is_discord_available:
        logger.warning("Discord not available, status notification not sent")
        return False

    try:
        # Send to the appropriate channel
        if test_mode:
            return send_test_message(status_message)
        else:
            return send_status_update(status_message)
    except Exception as e:
        logger.error(f"Error sending status notification: {e}")
        return False

def notify_error(error_type: str, details: str, test_mode: bool = False) -> bool:
    """
    Send an error notification.

    Args:
        error_type: Type of error
        details: Error details
        test_mode: Whether to send to test channel (default: False)

    Returns:
        Success status
    """
    if not is_discord_available:
        logger.warning("Discord not available, error notification not sent")
        return False

    try:
        # Send to the appropriate channel
        if test_mode:
            message = f"**Error [{error_type}]**: {details}"
            return send_test_message(message)
        else:
            return send_error_notification(error_type, details)
    except Exception as e:
        logger.error(f"Error sending error notification: {e}")
        return False

class NotificationManager:
    pass