#!/usr/bin/env python3
"""
Event Listener Watchdog

Monitors PostgreSQL LISTEN status and restarts ingestion listener if connections are lost.
Runs every 60 seconds to ensure event-driven pipeline remains active.
"""
import os
import time
import psycopg2
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
CHECK_INTERVAL = 60  # seconds
RESTART_THRESHOLD = 60  # seconds without LISTEN connection

class ListenerWatchdog:
    def __init__(self):
        self.last_listener_seen = datetime.now()
        self.restart_count = 0
        
    def check_listener_status(self):
        """Check if PostgreSQL LISTEN connection is active."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM pg_stat_activity 
                        WHERE query = 'LISTEN "events"' AND state = 'idle'
                    """)
                    listener_count = cur.fetchone()[0]
                    
                    if listener_count > 0:
                        self.last_listener_seen = datetime.now()
                        logger.info(f"✅ Event listener active ({listener_count} connections)")
                        return True
                    else:
                        time_since_last = datetime.now() - self.last_listener_seen
                        logger.warning(f"❌ No active LISTEN connections found (last seen: {time_since_last.total_seconds():.0f}s ago)")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to check listener status: {e}")
            return False
    
    def restart_listener(self):
        """Attempt to restart the ingestion listener."""
        try:
            logger.warning(f"🔄 Attempting to restart ingestion listener (restart #{self.restart_count + 1})")
            
            # Import and restart listener within app context
            import sys
            sys.path.append('/home/runner/workspace')
            
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from features.ingestion.restart_helper import restart_listener
                success = restart_listener()
                
                if success:
                    self.restart_count += 1
                    self.last_listener_seen = datetime.now()
                    logger.info(f"✅ Ingestion listener restarted successfully")
                    return True
                else:
                    logger.error("❌ Failed to restart ingestion listener")
                    return False
                    
        except Exception as e:
            logger.error(f"Error during listener restart: {e}")
            return False
    
    def monitor(self):
        """Main monitoring loop."""
        logger.info("🔍 Starting Event Listener Watchdog")
        
        while True:
            try:
                is_active = self.check_listener_status()
                
                if not is_active:
                    time_since_last = datetime.now() - self.last_listener_seen
                    
                    if time_since_last.total_seconds() > RESTART_THRESHOLD:
                        logger.critical(f"⚠️ LISTENER DOWN for {time_since_last.total_seconds():.0f}s - attempting restart")
                        
                        restart_success = self.restart_listener()
                        if not restart_success:
                            logger.critical("❌ CRITICAL: Unable to restart listener - manual intervention required")
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("🛑 Watchdog stopped by user")
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    watchdog = ListenerWatchdog()
    watchdog.monitor()