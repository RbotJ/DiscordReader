"""
Event System (PostgreSQL-based) - DEPRECATED

This module is deprecated. Use common.db.publish_event instead.
Kept for backward compatibility during migration.
"""

import logging
import warnings
from typing import Dict, Any

# Import the canonical implementation
from common.db import publish_event as _canonical_publish_event, get_latest_events

logger = logging.getLogger(__name__)

# Compatibility stubs for deprecated functions
class EventClient:
    """Deprecated event client. Use common.db functions directly."""
    
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        warnings.warn("EventClient is deprecated. Use common.db.publish_event instead.", DeprecationWarning)
        return _canonical_publish_event("legacy", data, channel)

# Global instance for backward compatibility
event_client = EventClient()

def subscribe_to_events(channel: str, callback=None):
    """Deprecated function for backward compatibility."""
    warnings.warn("subscribe_to_events is deprecated. Use common.db.get_latest_events instead.", DeprecationWarning)
    return get_latest_events(channel)

def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """
    DEPRECATED: Use common.db.publish_event instead.
    
    This is a compatibility wrapper that redirects to the canonical implementation.
    """
    warnings.warn(
        "common.event_compat.publish_event is deprecated. Use common.db.publish_event instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _canonical_publish_event(channel, data)

def get_latest_events(channel: str, since_timestamp=None, limit: int = 100):
    """Query the latest events for a given channel."""
    from datetime import datetime
    from typing import List, Dict, Any, Optional
    from common.models_db import EventModel
    from common.db import db
    
    try:
        query = db.session.query(EventModel).filter(
            EventModel.channel == channel
        )
        if since_timestamp:
            query = query.filter(EventModel.created_at > since_timestamp)

        events = query.order_by(EventModel.created_at.desc()).limit(limit).all()
        return [
            {
                'id': e.id,
                'channel': e.channel,
                'event_type': getattr(e, 'event_type', None),
                'data': e.data,
                'created_at': e.created_at
            } for e in events
        ]
    except Exception as e:
        logger.error(f"Failed to get latest events: {e}")
        return []
