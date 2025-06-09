"""
Parsing Service Module

Main service orchestrator for the parsing vertical slice.
Provides a unified interface for parsing functionality.
"""
import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional

from .parser import MessageParser
from .aplus_parser import get_aplus_parser
from .store import get_parsing_store
from .listener import get_parsing_listener
from .models import TradeSetup, ParsedLevel

logger = logging.getLogger(__name__)


class ParsingService:
    """
    Main service class for the parsing vertical slice.
    Orchestrates parser, store, and listener components.
    """
    
    def __init__(self):
        """Initialize the parsing service."""
        self.parser = MessageParser()
        self.aplus_parser = get_aplus_parser()
        self.store = get_parsing_store()
        self.listener = get_parsing_listener()
        self._initialized = False
        logger.info("Parsing service initialized")
    
    def start_service(self):
        """Start the parsing service listener."""
        try:
            if not self._initialized:
                self.listener.start_listening()
                self._initialized = True
                logger.info("Parsing service started successfully")
            else:
                logger.info("Parsing service already running")
        except Exception as e:
            logger.error(f"Error starting parsing service: {e}")
            raise
    
    def stop_service(self):
        """Stop the parsing service."""
        try:
            if self._initialized:
                self.listener.stop_listening()
                self._initialized = False
                logger.info("Parsing service stopped")
        except Exception as e:
            logger.error(f"Error stopping parsing service: {e}")
    
    def parse_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a message manually.
        
        Args:
            message_data: Dict containing message content and metadata
            
        Returns:
            Parsing results
        """
        return self.listener.process_message_manually(message_data)
    
    def parse_aplus_message(self, message_content: str, message_id: str, trading_day: Optional[date] = None) -> Dict[str, Any]:
        """
        Parse an A+ scalp setups message with enhanced schema fields.
        
        Args:
            message_content: Raw message content
            message_id: Discord message ID
            trading_day: Trading day (defaults to extracted date or today)
            
        Returns:
            Parsing results with enhanced setup data
        """
        try:
            # Check if this is an A+ message
            if not self.aplus_parser.validate_message(message_content):
                logger.warning(f"Message {message_id} is not a valid A+ scalp setups message")
                return {'success': False, 'error': 'Not an A+ scalp setups message'}
            
            # Parse the message
            parsed_data = self.aplus_parser.parse_message(message_content, message_id)
            
            if not parsed_data.get('success', False):
                logger.warning(f"Failed to parse A+ message {message_id}: {parsed_data.get('error', 'Unknown error')}")
                return parsed_data
            
            # Extract trading day from parsed data or use provided/default
            if trading_day is None:
                trading_day = parsed_data.get('trading_day') or date.today()
            
            # Store the parsed setups with enhanced schema
            aplus_setups = parsed_data.get('setups', [])
            if aplus_setups:
                created_setups, created_levels = self.store.store_parsed_message(
                    message_id=message_id,
                    setups=[],  # Empty for standard setups
                    levels_by_setup={},  # Empty for standard levels
                    trading_day=trading_day,
                    aplus_setups=aplus_setups  # Enhanced A+ setups with profile names
                )
                
                logger.info(f"Stored {len(created_setups)} A+ setups and {len(created_levels)} levels from message {message_id}")
                
                # Return enhanced results
                return {
                    'success': True,
                    'message_id': message_id,
                    'trading_day': trading_day.isoformat(),
                    'setups_created': len(created_setups),
                    'levels_created': len(created_levels),
                    'enhanced_features': {
                        'profile_names': [setup.profile_name for setup in created_setups if hasattr(setup, 'profile_name')],
                        'trigger_levels': [float(setup.trigger_level) for setup in created_setups if hasattr(setup, 'trigger_level') and setup.trigger_level],
                        'entry_conditions': [setup.entry_condition for setup in created_setups if hasattr(setup, 'entry_condition')]
                    },
                    'tickers': list(set(setup.ticker for setup in created_setups))
                }
            else:
                logger.warning(f"No A+ setups found in message {message_id}")
                return {'success': False, 'error': 'No valid setups found in message'}
                
        except Exception as e:
            logger.error(f"Error parsing A+ message {message_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_active_setups(self, trading_day: Optional[date] = None, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active setups with optional filtering.
        
        Args:
            trading_day: Optional trading day filter
            ticker: Optional ticker filter
            
        Returns:
            List of setup dictionaries
        """
        try:
            if trading_day is None:
                trading_day = date.today()
            
            setups = self.store.get_active_setups_for_day(trading_day)
            
            # Filter by ticker if specified
            if ticker:
                setups = [setup for setup in setups if setup.ticker.upper() == ticker.upper()]
            
            # Convert to dict format with levels
            result = []
            for setup in setups:
                setup_dict = setup.to_dict()
                levels = self.store.get_levels_by_setup(setup.id)
                setup_dict['levels'] = [level.to_dict() for level in levels]
                result.append(setup_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting active setups: {e}")
            return []
    
    def get_setup_by_id(self, setup_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific setup by ID.
        
        Args:
            setup_id: Setup ID
            
        Returns:
            Setup dictionary or None
        """
        try:
            from .models import TradeSetup
            setup = self.store.session.query(TradeSetup).filter_by(id=setup_id).first()
            
            if not setup:
                return None
            
            setup_dict = setup.to_dict()
            levels = self.store.get_levels_by_setup(setup_id)
            setup_dict['levels'] = [level.to_dict() for level in levels]
            
            return setup_dict
            
        except Exception as e:
            logger.error(f"Error getting setup {setup_id}: {e}")
            return None
    
    def deactivate_setup(self, setup_id: int) -> bool:
        """Deactivate a setup."""
        return self.store.deactivate_setup(setup_id)
    
    def trigger_level(self, level_id: int) -> bool:
        """Trigger a level."""
        return self.store.trigger_level(level_id)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive service statistics.
        
        Returns:
            Service statistics dictionary
        """
        try:
            parsing_stats = self.store.get_parsing_statistics()
            listener_stats = self.listener.get_stats()
            
            return {
                'service_status': 'running' if self._initialized else 'stopped',
                'service_type': 'parsing',
                'parsing_stats': parsing_stats,
                'listener_stats': listener_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {
                'service_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def is_healthy(self) -> bool:
        """Check if the parsing service is healthy."""
        try:
            # Check if listener is running
            if not self._initialized:
                return False
            
            # Check if we can get stats
            stats = self.listener.get_stats()
            return stats.get('status') == 'active'
            
        except Exception:
            return False


# Global service instance
_service = None

def get_parsing_service() -> ParsingService:
    """Get the global parsing service instance."""
    global _service
    if _service is None:
        _service = ParsingService()
    return _service

def start_parsing_service():
    """Start the parsing service."""
    service = get_parsing_service()
    service.start_service()
    return service

def stop_parsing_service():
    """Stop the parsing service."""
    service = get_parsing_service()
    service.stop_service()