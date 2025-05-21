"""
Event Publisher Module

Publishes events using PostgreSQL-based event system.
"""
import logging
from common.events import publish_event, EventChannels
from common.db import db

logger = logging.getLogger(__name__)

def publish_setup_event(setup_data):
    """Publish a setup event."""
    return publish_event(EventChannels.SETUP_CREATED, setup_data)

def publish_signal_event(signal_data):
    """Publish a signal event."""
    return publish_event(EventChannels.SIGNAL_TRIGGERED, signal_data)

def publish_trade_event(trade_data):
    """Publish a trade execution event."""
    return publish_event(EventChannels.TRADE_EXECUTED, trade_data)