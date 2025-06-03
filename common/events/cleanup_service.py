"""
Event Cleanup Service

Handles automated cleanup of events older than 90 days per retention policy.
Integrates with Flask application lifecycle for scheduled maintenance.
"""
import logging
import schedule
import threading
import time
from datetime import datetime, timedelta

from .query_service import EventQueryService
from .constants import EventChannels, EventTypes
from common.events.publisher import publish_event_safe as publish_event

logger = logging.getLogger(__name__)


class EventCleanupService:
    """Service for automated event cleanup and maintenance."""
    
    def __init__(self):
        self.running = False
        self.cleanup_thread = None
    
    def start_cleanup_scheduler(self):
        """Start the automated cleanup scheduler."""
        if self.running:
            logger.warning("Event cleanup scheduler already running")
            return
        
        # Schedule daily cleanup at 2 AM
        schedule.every().day.at("02:00").do(self.run_cleanup)
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("Event cleanup scheduler started")
        
        # Publish startup event
        publish_event(
            event_type=EventTypes.INFO,
            data={'service': 'event_cleanup', 'status': 'started'},
            channel=EventChannels.SYSTEM,
            source='event_cleanup_service'
        )
    
    def stop_cleanup_scheduler(self):
        """Stop the automated cleanup scheduler."""
        self.running = False
        schedule.clear()
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Event cleanup scheduler stopped")
        
        # Publish shutdown event
        publish_event(
            event_type=EventTypes.INFO,
            data={'service': 'event_cleanup', 'status': 'stopped'},
            channel=EventChannels.SYSTEM,
            source='event_cleanup_service'
        )
    
    def run_cleanup(self):
        """Execute the event cleanup operation."""
        try:
            logger.info("Starting scheduled event cleanup")
            
            start_time = datetime.utcnow()
            deleted_count = EventQueryService.cleanup_old_events()
            end_time = datetime.utcnow()
            
            duration = (end_time - start_time).total_seconds()
            
            # Publish cleanup completion event
            publish_event(
                event_type=EventTypes.INFO,
                data={
                    'cleanup_completed': True,
                    'events_deleted': deleted_count,
                    'duration_seconds': duration,
                    'cleanup_date': start_time.isoformat()
                },
                channel=EventChannels.SYSTEM,
                source='event_cleanup_service'
            )
            
            logger.info(f"Event cleanup completed: {deleted_count} events deleted in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during scheduled event cleanup: {e}")
            
            # Publish cleanup error event
            publish_event(
                event_type=EventTypes.ERROR,
                data={
                    'cleanup_failed': True,
                    'error': str(e),
                    'cleanup_date': datetime.utcnow().isoformat()
                },
                channel=EventChannels.SYSTEM,
                source='event_cleanup_service'
            )
    
    def _scheduler_loop(self):
        """Internal scheduler loop for cleanup tasks."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in cleanup scheduler loop: {e}")
                time.sleep(60)
    
    def force_cleanup(self):
        """Force immediate cleanup operation (for testing/manual triggers)."""
        logger.info("Forcing immediate event cleanup")
        self.run_cleanup()


# Global cleanup service instance
cleanup_service = EventCleanupService()