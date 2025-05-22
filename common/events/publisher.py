"""
Event Publisher Module

Handles publishing events to the PostgreSQL event system.
"""
import logging
from typing import Dict, Any

from common.events import EventSystem
from common.events.constants import EventChannels

# Create a logger for this module
logger = logging.getLogger(__name__)

def publish_event(channel: str, payload: Dict[str, Any]) -> bool:
    """
    Publish an event to a channel.
    
    Args:
        channel: The channel to publish to
        payload: The event payload
        
    Returns:
        True if successful, False otherwise
    """
    return EventSystem.publish_event(channel, payload)

def publish_discord_message(message_data: Dict[str, Any]) -> bool:
    """
    Publish Discord message event.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    return publish_event(EventChannels.DISCORD_MESSAGE, message_data)

def publish_discord_setup(setup_data: Dict[str, Any]) -> bool:
    """
    Publish Discord setup event.
    
    Args:
        setup_data: Dictionary containing setup data
        
    Returns:
        True if successful, False otherwise
    """
    return publish_event(EventChannels.DISCORD_SETUP, setup_data)

def publish_trade_executed(trade_data: Dict[str, Any]) -> bool:
    """
    Publish trade executed event.
    
    Args:
        trade_data: Dictionary containing trade data
        
    Returns:
        True if successful, False otherwise
    """
    return publish_event(EventChannels.TRADE_EXECUTED, trade_data)

def publish_ticker_data(ticker_data: Dict[str, Any]) -> bool:
    """
    Publish ticker data event.
    
    Args:
        ticker_data: Dictionary containing ticker data
        
    Returns:
        True if successful, False otherwise
    """
    return publish_event(EventChannels.TICKER_DATA, ticker_data)

def publish_alert_triggered(alert_data: Dict[str, Any]) -> bool:
    """
    Publish alert triggered event.
    
    Args:
        alert_data: Dictionary containing alert data
        
    Returns:
        True if successful, False otherwise
    """
    return publish_event(EventChannels.ALERT_TRIGGERED, alert_data)