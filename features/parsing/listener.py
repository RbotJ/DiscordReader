"""
Parsing Event Listener Module

Listens for MESSAGE_STORED events and triggers parsing workflow.
This module handles the event-driven parsing of Discord messages,
orchestrating the parse → store → emit SETUP_PARSED workflow.
"""
import logging
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from .parser import MessageParser
from .rules import APlusRulesEngine, analyze_message_with_aplus_rules
from .store import SetupStorageService
from .models import SetupModel
from features.ingestion.models import DiscordMessageModel
from common.db import get_latest_events, publish_event
from common.event_constants import EventChannels, EventType

logger = logging.getLogger(__name__)


class ParsingEventListener:
    """
    Listens for Discord message events and triggers parsing workflow.
    
    This class handles the event-driven architecture for message parsing,
    responding to MESSAGE_STORED events by parsing and storing setups.
    """
    
    def __init__(self):
        """Initialize parsing event listener with required components."""
        self.parser = MessageParser()
        self.rules_engine = APlusRulesEngine()
        self.storage_service = SetupStorageService()
        self.is_running = False
        self.stats = {
            'messages_processed': 0,
            'setups_parsed': 0,
            'errors': 0
        }
    
    async def start_listening(self) -> None:
        """
        Start listening for MESSAGE_STORED events.
        
        This method begins the event listening loop that processes
        incoming message events and triggers parsing workflows.
        """
        logger.info("Starting parsing event listener")
        self.is_running = True
        
        try:
            while self.is_running:
                await self._process_pending_events()
                await asyncio.sleep(5)  # Check for new events every 5 seconds
                
        except Exception as e:
            logger.error(f"Error in parsing event listener: {e}")
            raise
    
    def stop_listening(self) -> None:
        """Stop the event listener."""
        logger.info("Stopping parsing event listener")
        self.is_running = False
    
    async def _process_pending_events(self) -> None:
        """
        Process pending MESSAGE_STORED events.
        
        Retrieves recent message events and processes them for parsing.
        """
        try:
            # Get recent MESSAGE_STORED events
            events = get_latest_events(
                channel=EventChannels.DISCORD_MESSAGE,
                limit=50
            )
            
            for event in events:
                if event.get('event_type') == 'MESSAGE_STORED':
                    await self._handle_message_stored_event(event)
                    
        except Exception as e:
            logger.error(f"Error processing pending events: {e}")
    
    async def _handle_message_stored_event(self, event: Dict[str, Any]) -> None:
        """
        Handle a MESSAGE_STORED event by parsing the message.
        
        Args:
            event: Event data containing message information
        """
        try:
            payload = event.get('payload', {})
            message_id = payload.get('message_id')
            
            if not message_id:
                logger.warning("MESSAGE_STORED event missing message_id")
                return
            
            # Get the stored message from database
            message = DiscordMessageModel.get_by_message_id(message_id)
            if not message:
                logger.warning(f"Message {message_id} not found in database")
                return
            
            # Skip if already processed
            if message.is_processed:
                return
            
            # Parse the message
            await self._parse_and_store_message(message)
            
            # Mark message as processed
            message.mark_as_processed()
            
            self.stats['messages_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error handling MESSAGE_STORED event: {e}")
            self.stats['errors'] += 1
    
    async def _parse_and_store_message(self, message: DiscordMessageModel) -> None:
        """
        Parse a message and store any extracted setups.
        
        Args:
            message: DiscordMessageModel to parse
        """
        try:
            # Parse message content for trading setups
            setups = self.parser.parse_message(
                message.content, 
                message.message_id
            )
            
            if not setups:
                logger.debug(f"No setups found in message {message.message_id}")
                return
            
            # Apply A+ rules analysis to each setup
            enhanced_setups = []
            for setup in setups:
                enhanced_setup = self._enhance_setup_with_rules(setup, message.content)
                enhanced_setups.append(enhanced_setup)
            
            # Store setups in database
            storage_results = self.storage_service.store_setup_batch(enhanced_setups)
            
            # Update statistics
            self.stats['setups_parsed'] += storage_results['successfully_stored']
            
            # Emit SETUP_PARSED events for successfully stored setups
            for setup in storage_results['stored_setups']:
                await self._emit_setup_parsed_event(setup, message)
            
            logger.info(f"Processed message {message.message_id}: {len(enhanced_setups)} setups parsed")
            
        except Exception as e:
            logger.error(f"Error parsing and storing message {message.message_id}: {e}")
            self.stats['errors'] += 1
    
    def _enhance_setup_with_rules(self, setup: SetupModel, message_content: str) -> SetupModel:
        """
        Enhance setup with A+ rules analysis.
        
        Args:
            setup: Base setup model from parser
            message_content: Original message content for rules analysis
            
        Returns:
            SetupModel: Enhanced setup with A+ rules applied
        """
        try:
            # Apply A+ rules analysis
            rules_analysis = analyze_message_with_aplus_rules(message_content)
            
            # Enhance setup with rules analysis
            setup.aggressiveness = rules_analysis['aggressiveness'].value
            
            # Add risk parameters
            risk_params = rules_analysis['risk_parameters']
            if risk_params.get('stop_loss'):
                setup.stop_loss = risk_params['stop_loss']
            if risk_params.get('position_size_hint'):
                setup.position_size_hint = risk_params['position_size_hint']
            
            # Adjust confidence based on rules
            if rules_analysis['conservative_short']['detected']:
                setup.confidence = max(setup.confidence, rules_analysis['conservative_short']['confidence'])
                setup.setup_type = 'conservative_short'
            
            if rules_analysis['aggressive_long']['detected']:
                setup.confidence = max(setup.confidence, rules_analysis['aggressive_long']['confidence'])
                setup.setup_type = 'aggressive_long'
            
            return setup
            
        except Exception as e:
            logger.error(f"Error enhancing setup with rules: {e}")
            return setup
    
    async def _emit_setup_parsed_event(self, setup: SetupModel, message: DiscordMessageModel) -> None:
        """
        Emit SETUP_PARSED event for a successfully parsed setup.
        
        Args:
            setup: SetupModel that was parsed and stored
            message: Original DiscordMessageModel
        """
        try:
            event_payload = {
                'setup_id': setup.id,
                'ticker': setup.ticker,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'confidence': setup.confidence,
                'source_message_id': message.message_id,
                'channel_id': message.channel_id,
                'parsed_at': datetime.utcnow().isoformat()
            }
            
            publish_event(
                event_type=EventType.SETUP_PARSED,
                payload=event_payload,
                channel=EventChannels.SETUP_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error emitting SETUP_PARSED event: {e}")
    
    def get_listener_stats(self) -> Dict[str, Any]:
        """
        Get listener statistics.
        
        Returns:
            Dict[str, Any]: Listener performance statistics
        """
        return {
            'is_running': self.is_running,
            'statistics': self.stats.copy(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def reset_stats(self) -> None:
        """Reset listener statistics."""
        self.stats = {
            'messages_processed': 0,
            'setups_parsed': 0,
            'errors': 0
        }


async def process_message_for_parsing(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to process a single message for parsing.
    
    Args:
        message_id: Discord message ID to process
        
    Returns:
        Optional[Dict[str, Any]]: Processing results or None if failed
    """
    listener = ParsingEventListener()
    
    # Get message from database
    message = DiscordMessageModel.get_by_message_id(message_id)
    if not message:
        return None
    
    # Parse and store
    await listener._parse_and_store_message(message)
    
    return listener.get_listener_stats()


def start_parsing_listener() -> ParsingEventListener:
    """
    Start the parsing event listener.
    
    Returns:
        ParsingEventListener: Started listener instance
    """
    listener = ParsingEventListener()
    asyncio.create_task(listener.start_listening())
    return listener