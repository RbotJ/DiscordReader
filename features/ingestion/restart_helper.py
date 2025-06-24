"""
Ingestion Listener Restart Helper

Provides functionality to restart the ingestion listener for watchdog and recovery scripts.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def restart_ingestion_listener() -> bool:
    """
    Restart the ingestion listener service.
    
    Returns:
        bool: True if restart was successful, False otherwise
    """
    try:
        # Import listener module
        from . import listener
        
        # Stop existing listener if running
        if hasattr(listener, '_global_listener') and listener._global_listener:
            if hasattr(listener._global_listener, 'running') and listener._global_listener.running:
                logger.info("Stopping existing ingestion listener")
                listener._global_listener.stop_listening()
                await asyncio.sleep(2)  # Allow cleanup time
        
        # Start fresh listener
        logger.info("Starting fresh ingestion listener")
        await listener.start_ingestion_listener()
        
        # Verify it started
        await asyncio.sleep(2)
        stats = listener.get_listener_stats()
        
        if stats.get('status') != 'not_running':
            logger.info("Ingestion listener restart successful")
            return True
        else:
            logger.error("Failed to restart ingestion listener")
            return False
            
    except Exception as e:
        logger.error(f"Error during ingestion listener restart: {e}")
        return False

def restart_listener() -> bool:
    """
    Synchronous wrapper for restarting ingestion listener.
    
    Returns:
        bool: True if restart was successful, False otherwise
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a task
                task = loop.create_task(restart_ingestion_listener())
                return True  # Return immediately, check status later
            else:
                return loop.run_until_complete(restart_ingestion_listener())
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(restart_ingestion_listener())
    except Exception as e:
        logger.error(f"Failed to restart listener: {e}")
        return False