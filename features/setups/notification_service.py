"""
Notification Service

Handles setup notifications using PostgreSQL-based event system.
"""
import logging
from datetime import datetime
from common.events import publish_event, EventChannels
from common.db import db

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling setup notifications."""

    @staticmethod
    def notify_setup_created(setup_data):
        """Notify when a new setup is created."""
        event_data = {
            'event_type': 'setup_created',
            'timestamp': datetime.utcnow().isoformat(),
            'data': setup_data
        }
        return publish_event(EventChannels.SETUP_CREATED, event_data)

    @staticmethod
    def notify_setup_updated(setup_data):
        """Notify when a setup is updated."""
        event_data = {
            'event_type': 'setup_updated',
            'timestamp': datetime.utcnow().isoformat(),
            'data': setup_data
        }
        return publish_event(EventChannels.SETUP_UPDATED, event_data)