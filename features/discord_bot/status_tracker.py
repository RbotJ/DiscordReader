"""
Discord Bot Status Tracker

Event-driven status tracking for Discord gateway connection monitoring.
Provides real-time metrics for connection state, latency, and uptime.
"""
import asyncio
from datetime import datetime
from typing import Optional
import logging
from discord.ext import tasks

logger = logging.getLogger(__name__)


class BotStatusTracker:
    """Tracks Discord bot connection status through event listeners."""
    
    def __init__(self, bot):
        """Initialize status tracker with Discord bot instance."""
        self.is_online = False
        self.last_ready: Optional[datetime] = None
        self.last_disconnect: Optional[datetime] = None
        self.reconnects = 0
        self.latency_ms: Optional[float] = None
        self.last_event: Optional[datetime] = None
        
        # Store bot reference
        self._bot = bot
    
    async def on_ready(self):
        """Handle bot ready event - gateway connection established."""
        self.is_online = True
        self.last_ready = datetime.utcnow()
        self.last_event = datetime.utcnow()
        logger.info(f"Bot status: Online at {self.last_ready}")
        
        # Start latency tracking task
        if not self.track_latency.is_running():
            self.track_latency.start()
    
    async def on_disconnect(self):
        """Handle bot disconnect event - gateway connection lost."""
        self.is_online = False
        self.last_disconnect = datetime.utcnow()
        logger.warning(f"Bot status: Disconnected at {self.last_disconnect}")
        
        # Stop latency tracking when disconnected
        if self.track_latency.is_running():
            self.track_latency.cancel()
    
    async def on_resumed(self):
        """Handle bot resumed event - connection restored after disconnect."""
        self.reconnects += 1
        self.is_online = True
        logger.info(f"Bot status: Resumed (reconnect #{self.reconnects})")
    
    async def on_message(self, message):
        """Track last event timestamp to detect silent failures."""
        self.last_event = datetime.utcnow()
    
    @tasks.loop(seconds=5.0)
    async def track_latency(self):
        """Use discord.py's tasks.loop for periodic latency tracking."""
        try:
            if self._bot and hasattr(self._bot, 'latency') and self._bot.latency is not None:
                # Convert from seconds to milliseconds
                self.latency_ms = round(self._bot.latency * 1000, 1)
        except Exception as e:
            logger.warning(f"Error tracking latency: {e}")
    
    def get_status(self) -> dict:
        """
        Get current bot status as dictionary for API consumption.
        
        Returns:
            dict: Complete status information
        """
        uptime_seconds = 0
        if self.is_online and self.last_ready:
            uptime_seconds = int((datetime.utcnow() - self.last_ready).total_seconds())
        
        return {
            'connected': self.is_online,
            'last_ready': self.last_ready.isoformat() if self.last_ready else None,
            'last_disconnect': self.last_disconnect.isoformat() if self.last_disconnect else None,
            'latency_ms': self.latency_ms,
            'reconnects': self.reconnects,
            'uptime_seconds': uptime_seconds,
            'last_event': self.last_event.isoformat() if self.last_event else None
        }
    
    def cleanup(self):
        """Clean up background tasks."""
        if self.track_latency.is_running():
            self.track_latency.cancel()


# Global status tracker instance
_status_tracker: Optional[BotStatusTracker] = None


def initialize_status_tracker(bot) -> BotStatusTracker:
    """Initialize global status tracker with bot instance."""
    global _status_tracker
    if _status_tracker is None:
        _status_tracker = BotStatusTracker(bot)
    return _status_tracker


def get_status_tracker() -> Optional[BotStatusTracker]:
    """Get the global status tracker instance."""
    return _status_tracker