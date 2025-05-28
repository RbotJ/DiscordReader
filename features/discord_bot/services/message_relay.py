"""
Message Relay Service

Handles clean ingestion triggering and alert routing.
Provides clean interface between bot events and ingestion pipeline.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from features.ingestion.service import IngestionService

logger = logging.getLogger(__name__)


class MessageRelay:
    """Service for relaying messages between Discord bot and internal systems."""

    def __init__(self, ingestion_service: IngestionService):
        """
        Initialize message relay.
        
        Args:
            ingestion_service: Configured ingestion service instance
        """
        self.ingestion_service = ingestion_service
        self.relay_stats = {
            'messages_relayed': 0,
            'ingestion_triggers': 0,
            'alert_routes': 0,
            'errors': 0
        }

    async def relay_message_for_ingestion(self, channel_id: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """
        Relay message event to ingestion pipeline.
        
        Args:
            channel_id: Discord channel ID where message was posted
            limit: Number of recent messages to ingest
            
        Returns:
            Optional[Dict[str, Any]]: Ingestion result or None if failed
        """
        try:
            logger.info(f"Relaying message from channel {channel_id} to ingestion pipeline")
            
            # Trigger ingestion with timestamp tracking
            result = await self.ingestion_service.ingest_latest_messages(
                channel_id=channel_id,
                limit=limit,
                since=self.ingestion_service.get_last_triggered()
            )
            
            self.relay_stats['messages_relayed'] += 1
            self.relay_stats['ingestion_triggers'] += 1
            
            logger.info(f"Successfully relayed message for ingestion: {result.get('statistics', {})}")
            return result
            
        except Exception as e:
            logger.error(f"Error relaying message for ingestion: {e}")
            self.relay_stats['errors'] += 1
            return None

    async def route_alert_to_discord(self, alert_data: Dict[str, Any], target_channel: str) -> bool:
        """
        Route alert from internal systems to Discord channel.
        Placeholder for future alerts integration.
        
        Args:
            alert_data: Alert information to send
            target_channel: Discord channel ID to send alert to
            
        Returns:
            bool: True if alert was routed successfully
        """
        try:
            # Placeholder implementation for future alerts feature
            logger.info(f"Alert routing placeholder: {alert_data.get('type', 'unknown')} -> {target_channel}")
            
            # TODO: Implement actual Discord message sending when alerts feature is ready
            # This will interface with /features/alerts/ when that system is developed
            
            self.relay_stats['alert_routes'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error routing alert to Discord: {e}")
            self.relay_stats['errors'] += 1
            return False

    def get_relay_stats(self) -> Dict[str, int]:
        """
        Get message relay statistics.
        
        Returns:
            Dict[str, int]: Relay statistics for monitoring
        """
        return self.relay_stats.copy()

    def reset_relay_stats(self) -> None:
        """Reset relay statistics."""
        self.relay_stats = {
            'messages_relayed': 0,
            'ingestion_triggers': 0,
            'alert_routes': 0,
            'errors': 0
        }