"""
Centralized Event System

Provides unified event handling across the trading application.
Exports all necessary event components from their respective modules.
"""

from .constants import EventChannels, EventTypes
from .publisher import publish_event, publish_event_safe, flush_event_buffer
from .consumer import (
    get_events_by_channel,
    get_latest_events,
    get_events_by_correlation_id,
    poll_events,
    get_latest_event_id
    # subscribe_to_events deprecated - use publisher.listen_for_events instead
)
from .models import Event

__all__ = [
    # Constants
    'EventChannels',
    'EventTypes',
    
    # Publisher functions
    'publish_event',
    'publish_event_safe', 
    'flush_event_buffer',
    
    # Consumer functions
    'get_events_by_channel',
    'get_latest_events',
    'get_events_by_correlation_id',
    'poll_events',
    'get_latest_event_id',
    'subscribe_to_events',
    
    # Models
    'Event'
]