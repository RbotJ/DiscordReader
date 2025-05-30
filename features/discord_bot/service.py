"""
Discord Bot Service

Service layer for Discord bot management, providing metrics and operational data
without exposing internal bot implementation details.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BotService:
    """Service for Discord bot operational metrics and status management."""
    
    def __init__(self):
        """Initialize the bot service."""
        self._connection_attempts = 0
        self._successful_connections = 0
        self._last_ready_time = None
        self._start_time = datetime.utcnow()
    
    def get_metrics(self) -> dict:
        """
        Get Discord bot metrics for operational monitoring.
        
        Returns:
            dict: Metrics data for dashboard consumption
        """
        try:
            from common.db import db
            from .status_tracker import get_status_tracker
            
            # Get real status from event-driven tracker
            status_tracker = get_status_tracker()
            if status_tracker:
                tracker_status = status_tracker.get_status()
                status = 'connected' if tracker_status['connected'] else 'disconnected'
                uptime_seconds = tracker_status['uptime_seconds']
                latency_ms = tracker_status['latency_ms'] or 0
                last_ready = tracker_status['last_ready']
                reconnects = tracker_status['reconnects']
                last_activity = tracker_status['last_event']
            else:
                # Fallback to basic detection
                status = self._get_bot_status()
                uptime_seconds = 0
                latency_ms = 0
                last_ready = None
                reconnects = 0
                last_activity = None
            
            # Count messages processed today (if bot is processing)
            today = datetime.utcnow().date()
            messages_today = 0
            if status == 'connected':
                try:
                    messages_today = db.session.execute(
                        db.text("SELECT COUNT(*) FROM discord_messages WHERE DATE(created_at) = :today"),
                        {'today': today}
                    ).scalar() or 0
                except Exception:
                    pass
            
            # Get recent activity
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_activity = 0
            try:
                recent_activity = db.session.execute(
                    db.text("SELECT COUNT(*) FROM discord_messages WHERE created_at >= :hour_ago"),
                    {'hour_ago': hour_ago}
                ).scalar() or 0
            except Exception:
                pass
            
            # Get monitored channels count
            channels_monitored = 0
            try:
                channels_monitored = db.session.execute(
                    db.text("SELECT COUNT(*) FROM discord_channels WHERE is_listen = true")
                ).scalar() or 0
            except Exception:
                pass
            
            # Get last activity
            last_activity = None
            try:
                last_message_result = db.session.execute(
                    db.text("SELECT MAX(created_at) FROM discord_messages")
                ).scalar()
                if last_message_result:
                    last_activity = last_message_result.isoformat()
            except Exception:
                pass
            
            return {
                'status': status,
                'uptime_seconds': uptime_seconds,
                'messages_processed_today': messages_today,
                'messages_per_minute': recent_activity,
                'channels_monitored': channels_monitored,
                'error_count_last_hour': self._get_error_count(),
                'last_activity': last_activity,
                'connection_attempts': self._connection_attempts,
                'successful_connections': self._successful_connections,
                'last_ready': self._last_ready_time.isoformat() if self._last_ready_time else None,
                'error_message': self._get_error_message() if status in ['disabled', 'error'] else None
            }
            
        except Exception as e:
            logger.error(f"Error getting bot metrics: {e}")
            return {
                'status': 'error',
                'uptime_seconds': 0,
                'messages_processed_today': 0,
                'messages_per_minute': 0,
                'channels_monitored': 0,
                'error_count_last_hour': 0,
                'last_activity': None,
                'connection_attempts': self._connection_attempts,
                'successful_connections': self._successful_connections,
                'last_ready': None,
                'error_message': str(e)
            }
    
    def _get_bot_status(self) -> str:
        """
        Determine current bot status based on Discord gateway connection.
        
        Returns:
            str: One of 'connected', 'disconnected', 'error', 'disabled'
        """
        try:
            from features.discord_bot.bot import get_discord_client
            import os
            token = os.getenv("DISCORD_BOT_TOKEN")
            if not token:
                return 'disabled'
            
            # Check actual Discord client connection state
            client_manager = get_discord_client()
            if client_manager and hasattr(client_manager, 'client') and client_manager.client:
                client = client_manager.client
                # Use Discord.py's built-in connection state checks
                if client.is_ready():
                    return 'connected'
                elif not client.is_closed():
                    return 'connecting'
            
            return 'disconnected'
            
        except ImportError:
            return 'disabled'
        except Exception as e:
            logger.warning(f"Error checking bot status: {e}")
            return 'disconnected'
    
    def _get_error_count(self) -> int:
        """Get error count from logs or events in the last hour."""
        # Would need to implement error tracking
        return 0
    
    def _get_error_message(self) -> Optional[str]:
        """Get the current error message if bot is in error state."""
        try:
            import os
            token = os.getenv("DISCORD_BOT_TOKEN")
            if not token:
                return "Discord bot token not found - bot disabled"
            return "Discord bot dependencies not available - bot disabled"
        except Exception:
            return "Unknown error"
    
    def record_connection_attempt(self):
        """Record a connection attempt."""
        self._connection_attempts += 1
    
    def record_successful_connection(self):
        """Record a successful connection."""
        self._successful_connections += 1
        self._last_ready_time = datetime.utcnow()
    
    def record_disconnection(self):
        """Record a disconnection."""
        self._last_ready_time = None