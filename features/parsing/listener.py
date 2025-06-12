"""
Parsing Listener Module

Event listener for the parsing vertical slice.
Subscribes to ingestion events and processes Discord messages for trading setups.
"""
import logging
from datetime import datetime, date
from typing import Dict, Any, List

from common.events.consumer import EventConsumer
from common.events.publisher import publish_event
from .parser import MessageParser, ParsedSetupDTO, ParsedLevelDTO
from .store import ParsingStore, get_parsing_store
from .models import TradeSetup, ParsedLevel

logger = logging.getLogger(__name__)


class ParsingListener:
    """
    Event listener for parsing Discord messages into trade setups.
    Subscribes to MESSAGE_STORED events and publishes SETUP_PARSED events.
    """
    
    def __init__(self, app=None):
        """Initialize the parsing listener."""
        self.parser = MessageParser()
        self.store = get_parsing_store()
        self.stats = {
            'messages_processed': 0,
            'setups_created': 0,
            'levels_created': 0,
            'parsing_errors': 0,
            'storage_errors': 0,
            'last_processed': None
        }
        
        # Initialize event consumer with Flask app context
        self.consumer = EventConsumer('parsing', ['ingestion:message'], app=app)
        logger.info("Parsing listener initialized")
    
    def start_listening(self):
        """Start listening for ingestion events."""
        try:
            logger.info("Starting parsing listener...")
            self.consumer.subscribe('message.stored', self._handle_message_stored)
            self.consumer.start()
            logger.info("Parsing listener started successfully")
        except Exception as e:
            logger.error(f"Error starting parsing listener: {e}")
            raise
    
    def stop_listening(self):
        """Stop listening for events."""
        try:
            self.consumer.stop()
            logger.info("Parsing listener stopped")
        except Exception as e:
            logger.error(f"Error stopping parsing listener: {e}")
    
    def _handle_message_stored(self, event_data: Dict[str, Any]):
        """
        Handle MESSAGE_STORED event from ingestion.
        
        Args:
            event_data: Event data containing message information
        """
        try:
            logger.debug(f"Processing message stored event: {event_data.get('correlation_id', 'unknown')}")
            
            # Extract message information from event
            message_info = self._extract_message_info(event_data)
            if not message_info:
                logger.warning("Could not extract message info from event")
                return
            
            message_id = message_info['message_id']
            content = message_info['content']
            
            # Skip if message content is empty or too short
            if not content or len(content.strip()) < 10:
                logger.debug(f"Skipping message {message_id}: content too short")
                return
            
            # Check if this is an A+ message and route to specialized service
            from .aplus_parser import get_aplus_parser
            aplus_parser = get_aplus_parser()
            
            if aplus_parser.validate_message(content):
                logger.info(f"Routing A+ message {message_id} to specialized service")
                # Use specialized A+ service to preserve individual setups
                from .service import ParsingService
                service = ParsingService()
                result = service.parse_aplus_message(content, message_id)
                
                if result.get('success'):
                    setups_created = result.get('setups_created', 0)
                    levels_created = result.get('levels_created', 0)
                    
                    # Update stats
                    self.stats['messages_processed'] += 1
                    self.stats['setups_created'] += setups_created
                    self.stats['levels_created'] += levels_created
                    self.stats['last_processed'] = datetime.utcnow().isoformat()
                    
                    logger.info(f"A+ message {message_id} processed: {setups_created} setups, {levels_created} levels")
                    return
                else:
                    logger.warning(f"A+ service failed to process message {message_id}: {result.get('error')}")
                    # Fall through to generic parsing
            
            # Parse the message using enhanced parser
            parse_result = self.parser.parse_message_to_setups(message_info)
            
            if not parse_result.get('success') or not parse_result.get('setups'):
                logger.debug(f"No setups found in message {message_id}")
                self.stats['messages_processed'] += 1
                return
            
            setups = parse_result['setups']
            all_levels = parse_result['levels']
            trading_day = parse_result.get('trading_day')
            
            # Group levels by ticker
            levels_by_ticker = {}
            for setup in setups:
                ticker = setup.ticker
                # Find levels for this setup (they all come from the same message)
                ticker_levels = [level for level in all_levels if any(
                    kw in (level.description or '').lower() for kw in [ticker.lower()]
                )] if all_levels else []
                levels_by_ticker[ticker] = ticker_levels
            
            # Store parsed data
            try:
                # Use trading day from parser result if available, otherwise extract from message
                if not trading_day:
                    trading_day = self._extract_trading_day(message_info)
                created_setups, created_levels = self.store.store_parsed_message(
                    message_id, setups, levels_by_ticker, trading_day
                )
                
                # Update stats
                self.stats['messages_processed'] += 1
                self.stats['setups_created'] += len(created_setups)
                self.stats['levels_created'] += len(created_levels)
                self.stats['last_processed'] = datetime.utcnow().isoformat()
                
                # Emit SETUP_PARSED event for each created setup
                for setup in created_setups:
                    setup_levels = [level for level in created_levels if level.setup_id == setup.id]
                    self._emit_setup_parsed_event(setup, setup_levels, event_data.get('correlation_id'))
                
                logger.info(f"Successfully processed message {message_id}: "
                          f"{len(created_setups)} setups, {len(created_levels)} levels")
                
            except Exception as e:
                logger.error(f"Error storing parsed data for message {message_id}: {e}")
                self.stats['storage_errors'] += 1
            
        except Exception as e:
            logger.error(f"Error processing message stored event: {e}")
            self.stats['parsing_errors'] += 1
    
    def _extract_message_info(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message information from event data."""
        try:
            # Event data structure should contain message details
            data = event_data.get('data', {})
            
            # Try different possible structures
            if 'message' in data:
                message = data['message']
            elif 'message_data' in data:
                message = data['message_data']
            else:
                message = data
            
            # Extract required fields
            message_id = (
                message.get('message_id') or 
                message.get('id') or 
                event_data.get('source_id')
            )
            
            content = (
                message.get('content') or 
                message.get('text') or 
                message.get('message_content')
            )
            
            if not message_id or not content:
                logger.warning(f"Missing required fields in message data: {message}")
                return None
            
            return {
                'message_id': str(message_id),
                'content': str(content),
                'author_id': message.get('author_id'),
                'channel_id': message.get('channel_id'),
                'timestamp': message.get('timestamp'),
                'guild_id': message.get('guild_id')
            }
            
        except Exception as e:
            logger.error(f"Error extracting message info: {e}")
            return None
    
    def _extract_trading_day(self, message_info: Dict[str, Any]) -> date:
        """Extract trading day from message info."""
        try:
            # Try to parse timestamp from message
            timestamp_str = message_info.get('timestamp')
            if timestamp_str:
                # Handle different timestamp formats
                if isinstance(timestamp_str, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        return timestamp.date()
                    except (ValueError, TypeError):
                        pass
            
            # Default to today
            return date.today()
            
        except Exception as e:
            logger.warning(f"Error extracting trading day: {e}")
            return date.today()
    
    def _emit_setup_parsed_event(self, setup: TradeSetup, levels: List[ParsedLevel], correlation_id: str = None):
        """
        Emit SETUP_PARSED event for downstream consumers.
        
        Args:
            setup: Created TradeSetup instance
            levels: Associated ParsedLevel instances
            correlation_id: Event correlation ID for tracing
        """
        try:
            event_data = {
                'setup_id': setup.id,
                'ticker': setup.ticker,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'confidence_score': setup.confidence_score,
                'trading_day': setup.trading_day.isoformat(),
                'message_id': setup.message_id,
                'levels_count': len(levels),
                'levels': [
                    {
                        'id': level.id,
                        'level_type': level.level_type,
                        'trigger_price': float(level.trigger_price),
                        'direction': level.direction,
                        'strategy': level.strategy
                    }
                    for level in levels
                ],
                'metadata': {
                    'parsed_at': datetime.utcnow().isoformat(),
                    'parser_version': '1.0',
                    'confidence_threshold': 0.5
                }
            }
            
            publish_event(
                channel='parsing:setup',
                event_type='setup.parsed',
                data=event_data,
                source='parsing_listener',
                correlation_id=correlation_id
            )
            
            logger.debug(f"Emitted SETUP_PARSED event for setup {setup.id}")
            
        except Exception as e:
            logger.error(f"Error emitting setup parsed event: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parsing listener statistics."""
        return {
            **self.stats,
            'status': 'active' if self.consumer.is_running() else 'stopped',
            'parser_type': 'consolidated',
            'service_type': 'parsing'
        }
    
    def process_message_manually(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually process a message for testing or reprocessing.
        
        Args:
            message_data: Message data dict
            
        Returns:
            Processing results
        """
        try:
            # Parse the message using enhanced parser
            parse_result = self.parser.parse_message_to_setups(message_data)
            
            if not parse_result.get('success') or not parse_result.get('setups'):
                return {
                    'success': True,
                    'setups_created': 0,
                    'levels_created': 0,
                    'message': 'No setups found in message'
                }
            
            setups = parse_result['setups']
            all_levels = parse_result['levels']
            trading_date = parse_result.get('trading_day')
            
            # If parser didn't extract trading date, try A+ parser or fallback
            if not trading_date:
                content = message_data.get('content', '')
                
                # Check if this is A+ message and extract its trading date
                from .aplus_parser import get_aplus_parser
                aplus_parser = get_aplus_parser()
                if aplus_parser.validate_message(content):
                    trading_date = aplus_parser.extract_trading_date(content)
                    logger.info(f"Extracted A+ trading date: {trading_date}")
                
                # Fallback to message timestamp or today
                if not trading_date:
                    trading_date = self._extract_trading_day(message_data)
            
            # Group levels by ticker
            levels_by_ticker = {}
            for setup in setups:
                # For manual processing, assign all levels to the first setup
                if setup == setups[0]:
                    levels_by_ticker[setup.ticker] = all_levels
                else:
                    levels_by_ticker[setup.ticker] = []
            
            # Store the data with extracted trading date
            message_id = message_data.get('message_id', message_data.get('id'))
            created_setups, created_levels = self.store.store_parsed_message(
                message_id, setups, levels_by_ticker, trading_date
            )
            
            return {
                'success': True,
                'setups_created': len(created_setups),
                'levels_created': len(created_levels),
                'setups': [setup.to_dict() for setup in created_setups],
                'levels': [level.to_dict() for level in created_levels]
            }
            
        except Exception as e:
            logger.error(f"Error in manual message processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'setups_created': 0,
                'levels_created': 0
            }


# Global listener instance
_listener = None

def get_parsing_listener(app=None) -> ParsingListener:
    """Get the global parsing listener instance."""
    global _listener
    if _listener is None:
        _listener = ParsingListener(app=app)
    return _listener

def start_parsing_service():
    """Start the parsing service listener."""
    listener = get_parsing_listener()
    listener.start_listening()
    return listener

def stop_parsing_service():
    """Stop the parsing service listener."""
    listener = get_parsing_listener()
    listener.stop_listening()