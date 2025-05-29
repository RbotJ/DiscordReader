"""
Discord Bot Correlation Service

Provides correlation ID management for linking Discord messages through
the complete ingestion and parsing pipeline.
"""
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from common.events.enhanced_publisher import EventPublisher
from common.events.constants import EventChannels, EventTypes
from common.db import publish_event

logger = logging.getLogger(__name__)


class DiscordCorrelationService:
    """Service for managing correlation tracking in Discord message flows."""
    
    @staticmethod
    def generate_message_correlation_id() -> str:
        """
        Generate a new correlation ID for Discord message processing.
        
        Returns:
            str: New UUID correlation ID
        """
        correlation_id = str(uuid.uuid4())
        logger.debug(f"Generated correlation ID: {correlation_id}")
        return correlation_id
    
    @staticmethod
    def publish_message_received(
        message_data: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish Discord message received event with correlation tracking.
        
        Args:
            message_data: Discord message information
            correlation_id: Correlation UUID for this message flow
            
        Returns:
            bool: True if event published successfully
        """
        try:
            # Enhanced message data with correlation info
            enhanced_data = {
                **message_data,
                'flow_stage': 'message_received',
                'processing_started': datetime.utcnow().isoformat()
            }
            
            return publish_event(
                event_type=EventTypes.DISCORD_RECEIVED,
                payload=enhanced_data,
                channel=EventChannels.DISCORD_MESSAGE,
                source='discord_bot',
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error publishing message received event: {e}")
            return False
    
    @staticmethod
    def publish_message_processed(
        message_id: str,
        processing_result: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish Discord message processed event with results.
        
        Args:
            message_id: Discord message ID
            processing_result: Results of message processing
            correlation_id: Correlation UUID for this message flow
            
        Returns:
            bool: True if event published successfully
        """
        try:
            enhanced_data = {
                'message_id': message_id,
                'flow_stage': 'message_processed',
                'processing_completed': datetime.utcnow().isoformat(),
                **processing_result
            }
            
            return publish_event(
                event_type=EventTypes.DISCORD_PROCESSED,
                payload=enhanced_data,
                channel=EventChannels.DISCORD_MESSAGE,
                source='discord_bot',
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error publishing message processed event: {e}")
            return False
    
    @staticmethod
    def publish_ingestion_started(
        batch_info: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish ingestion batch started event.
        
        Args:
            batch_info: Information about the ingestion batch
            correlation_id: Correlation UUID for this flow
            
        Returns:
            bool: True if event published successfully
        """
        try:
            enhanced_data = {
                **batch_info,
                'flow_stage': 'ingestion_started',
                'ingestion_started': datetime.utcnow().isoformat()
            }
            
            return publish_event(
                event_type=EventTypes.CATCHUP_STARTED,
                payload=enhanced_data,
                channel=EventChannels.INGESTION_BATCH,
                source='discord_ingestion',
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error publishing ingestion started event: {e}")
            return False
    
    @staticmethod
    def publish_ingestion_completed(
        batch_results: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish ingestion batch completed event with results.
        
        Args:
            batch_results: Results of the ingestion batch
            correlation_id: Correlation UUID for this flow
            
        Returns:
            bool: True if event published successfully
        """
        try:
            enhanced_data = {
                **batch_results,
                'flow_stage': 'ingestion_completed',
                'ingestion_completed': datetime.utcnow().isoformat()
            }
            
            return publish_event(
                event_type=EventTypes.CATCHUP_COMPLETED,
                payload=enhanced_data,
                channel=EventChannels.INGESTION_BATCH,
                source='discord_ingestion',
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error publishing ingestion completed event: {e}")
            return False
    
    @staticmethod
    def publish_setup_parsing_started(
        message_info: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish setup parsing started event.
        
        Args:
            message_info: Information about the message being parsed
            correlation_id: Correlation UUID linking to original message
            
        Returns:
            bool: True if event published successfully
        """
        try:
            enhanced_data = {
                **message_info,
                'flow_stage': 'parsing_started',
                'parsing_started': datetime.utcnow().isoformat()
            }
            
            return publish_event(
                event_type=EventTypes.SETUP_PARSED,
                payload=enhanced_data,
                channel=EventChannels.PARSING_SETUP,
                source='discord_parser',
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error publishing setup parsing started event: {e}")
            return False
    
    @staticmethod
    def publish_setup_created(
        setup_data: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish setup created event linking back to original Discord message.
        
        Args:
            setup_data: Information about the created setup
            correlation_id: Correlation UUID linking to original message
            
        Returns:
            bool: True if event published successfully
        """
        try:
            enhanced_data = {
                **setup_data,
                'flow_stage': 'setup_created',
                'setup_created': datetime.utcnow().isoformat()
            }
            
            return publish_event(
                event_type=EventTypes.SETUP_CREATED,
                payload=enhanced_data,
                channel=EventChannels.SETUP_CREATED,
                source='setup_processor',
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error publishing setup created event: {e}")
            return False
    
    @staticmethod
    def get_message_correlation_flow(correlation_id: str) -> Dict[str, Any]:
        """
        Get the complete correlation flow for a Discord message.
        
        Args:
            correlation_id: Correlation UUID to trace
            
        Returns:
            Dict containing the complete flow information
        """
        try:
            from common.events.query_service import EventQueryService
            
            events = EventQueryService.get_events_by_correlation(correlation_id)
            
            if not events:
                return {
                    'correlation_id': correlation_id,
                    'flow': [],
                    'status': 'not_found'
                }
            
            # Organize events by flow stage
            flow_stages = {}
            for event in events:
                stage = event.data.get('flow_stage', 'unknown')
                flow_stages[stage] = {
                    'timestamp': event.created_at.isoformat(),
                    'channel': event.channel,
                    'event_type': event.event_type,
                    'source': event.source,
                    'data': event.data
                }
            
            # Determine flow completion status
            expected_stages = ['message_received', 'message_processed', 'ingestion_completed']
            completed_stages = list(flow_stages.keys())
            
            status = 'completed' if all(stage in completed_stages for stage in expected_stages) else 'in_progress'
            
            return {
                'correlation_id': correlation_id,
                'flow': flow_stages,
                'completed_stages': completed_stages,
                'status': status,
                'total_events': len(events)
            }
            
        except Exception as e:
            logger.error(f"Error getting correlation flow: {e}")
            return {
                'correlation_id': correlation_id,
                'flow': [],
                'status': 'error',
                'error': str(e)
            }