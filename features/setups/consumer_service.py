"""
Setup Message Consumer Service

This module provides a background service that consumes Discord setup messages
and processes them into structured data for charting and monitoring.
"""
import logging
import threading
import time
from typing import Optional

from features.setups.message_consumer import MessageConsumer
from common.events import EventChannels
from common.event_compat import event_client, subscribe_to_events, publish_event

logger = logging.getLogger(__name__)

_consumer_thread: Optional[threading.Thread] = None
_consumer_running: bool = False

def start_message_consumer_service():
    """Start the Discord message consumer service in a background thread."""
    global _consumer_thread, _consumer_running

    if _consumer_running:
        logger.info("Message consumer service is already running")
        return

    def _consumer_worker():
        """Worker function that runs in a separate thread."""
        try:
            logger.info("Starting message consumer worker thread")
            from app import app

            global _consumer_running
            _consumer_running = True

            # Subscribe to setup messages channel
            subscribe_to_events(DISCORD_SETUP_MESSAGE_CHANNEL)

            with app.app_context():
                consumer = MessageConsumer()
                consumer.start()
        except Exception as e:
            logger.error(f"Error in message consumer worker: {e}")
        finally:
            _consumer_running = False
            logger.info("Message consumer worker thread stopped")

    _consumer_thread = threading.Thread(
        target=_consumer_worker,
        name="SetupMessageConsumer",
        daemon=True
    )
    _consumer_thread.start()

    logger.info("Message consumer service started")
    return True

def stop_message_consumer_service():
    """Stop the Discord message consumer service."""
    global _consumer_thread, _consumer_running

    if not _consumer_running or not _consumer_thread:
        logger.info("Message consumer service is not running")
        return True

    _consumer_running = False

    if _consumer_thread:
        _consumer_thread.join(timeout=5.0)
        if _consumer_thread.is_alive():
            logger.warning("Message consumer thread did not terminate gracefully")
        else:
            logger.info("Message consumer thread terminated successfully")

    _consumer_thread = None
    return True

def is_consumer_running():
    """Check if the message consumer service is running."""
    global _consumer_running
    return _consumer_running