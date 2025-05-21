"""
Setup Message Consumer Service

This module provides a background service that consumes Discord setup messages
from Redis and processes them into structured data for charting and monitoring.
"""
import logging
import threading
import time
from typing import Optional

from features.setups.message_consumer import MessageConsumer

# Configure logger
logger = logging.getLogger(__name__)

# Global consumer thread reference
_consumer_thread: Optional[threading.Thread] = None
_consumer_running: bool = False

def start_message_consumer_service():
    """
    Start the Discord message consumer service in a background thread.
    """
    global _consumer_thread, _consumer_running
    
    if _consumer_running:
        logger.info("Message consumer service is already running")
        return
    
    def _consumer_worker():
        """Worker function that runs in a separate thread."""
        try:
            logger.info("Starting message consumer worker thread")
            from app import app
            
            # Set flag to indicate the service is running
            global _consumer_running
            _consumer_running = True
            
            # Start the consumer with Flask app context (blocking call)
            with app.app_context():
                consumer = MessageConsumer()
                consumer.start()
        except Exception as e:
            logger.error(f"Error in message consumer worker: {e}")
        finally:
            _consumer_running = False
            logger.info("Message consumer worker thread stopped")
    
    # Create and start the thread
    _consumer_thread = threading.Thread(
        target=_consumer_worker,
        name="SetupMessageConsumer",
        daemon=True  # Make thread terminate when main thread exits
    )
    _consumer_thread.start()
    
    logger.info("Message consumer service started")
    return True

def stop_message_consumer_service():
    """
    Stop the Discord message consumer service.
    """
    global _consumer_thread, _consumer_running
    
    if not _consumer_running or not _consumer_thread:
        logger.info("Message consumer service is not running")
        return True
    
    # Set flag to indicate service should stop
    _consumer_running = False
    
    # Wait for thread to terminate (with timeout)
    if _consumer_thread:
        _consumer_thread.join(timeout=5.0)
        if _consumer_thread.is_alive():
            logger.warning("Message consumer thread did not terminate gracefully")
        else:
            logger.info("Message consumer thread terminated successfully")
    
    _consumer_thread = None
    return True

def is_consumer_running():
    """
    Check if the message consumer service is running.
    
    Returns:
        bool: True if the service is running, False otherwise
    """
    global _consumer_running
    return _consumer_running