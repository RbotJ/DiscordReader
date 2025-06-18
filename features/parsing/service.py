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
from .store import get_parsing_store, DUPLICATE_POLICY
from .listener import get_parsing_listener
from .models import TradeSetup, ParsedLevel

logger = logging.getLogger(__name__)


class ParsingService:
    """
    Main service class for the parsing vertical slice.
    Orchestrates parser, store, and listener components.
    """
    
    def __init__(self, app=None):
        """Initialize the parsing service."""
        self.parser = MessageParser()
        self.aplus_parser = get_aplus_parser()
        self.store = get_parsing_store()
        self.listener = get_parsing_listener(app=app)
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
                # A+ parser returns 'trading_date' not 'trading_day'
                trading_day = parsed_data.get('trading_date') or parsed_data.get('trading_day')
                if not trading_day:
                    # Fallback: convert Discord message timestamp to NYSE trading day
                    import pytz
                    from datetime import datetime
                    nyse_tz = pytz.timezone('America/New_York')
                    # Get current time in NYSE timezone
                    nyse_now = datetime.now(nyse_tz)
                    trading_day = nyse_now.date()
                    logger.info(f"No trading date in message, using NYSE date: {trading_day}")
                else:
                    logger.info(f"Using extracted trading date: {trading_day}")
            
            # Duplicate detection logic
            duplicate_action = self._handle_duplicate_detection(message_id, trading_day, message_content, message_timestamp)
            if duplicate_action == "skip":
                logger.info(f"Skipping duplicate message {message_id} for trading day {trading_day}")
                return {'success': False, 'error': 'Duplicate message skipped', 'duplicate_detected': True}
            elif duplicate_action == "replaced":
                logger.info(f"Replaced existing setups for trading day {trading_day} with message {message_id}")
            
            # Store the parsed setups using new TradeSetup dataclass
            parsed_setups = parsed_data.get('setups', [])
            ticker_bias_notes = parsed_data.get('ticker_bias_notes', {})
            
            if parsed_setups:
                created_setups, created_levels = self.store.store_parsed_message(
                    message_id=message_id,
                    parsed_setups=parsed_setups,  # New TradeSetup dataclass instances
                    trading_day=trading_day,
                    ticker_bias_notes=ticker_bias_notes
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
                        'labels': [setup.label for setup in created_setups if hasattr(setup, 'label') and setup.label],
                        'trigger_levels': [float(setup.trigger_level) for setup in created_setups if hasattr(setup, 'trigger_level') and setup.trigger_level],
                        'directions': [setup.direction for setup in created_setups if hasattr(setup, 'direction') and setup.direction],
                        'keywords': [setup.keywords for setup in created_setups if hasattr(setup, 'keywords') and setup.keywords]
                    },
                    'tickers': list(set(setup.ticker for setup in created_setups))
                }
            else:
                logger.warning(f"No A+ setups found in message {message_id}")
                return {'success': False, 'error': 'No valid setups found in message'}
                
        except Exception as e:
            logger.error(f"Error parsing A+ message {message_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_duplicate_detection(self, message_id: str, trading_day: date, 
                                   message_content: str, message_timestamp: Optional[datetime] = None) -> str:
        """
        Handle duplicate detection logic based on configured policy.
        
        Args:
            message_id: Current message ID
            trading_day: Trading day extracted from message
            message_content: Raw message content
            message_timestamp: Message timestamp for comparison
            
        Returns:
            Action taken: "proceed", "skip", "replaced"
        """
        try:
            # Check if there's already a message for this trading day
            if not self.store.is_duplicate_setup(trading_day, message_id):
                return "proceed"  # No duplicate found
            
            # Get existing message details
            existing_details = self.store.find_existing_message_for_day(trading_day)
            if not existing_details:
                return "proceed"  # No existing message found
            
            existing_msg_id, existing_timestamp, existing_length = existing_details
            logger.info(f"Duplicate detected for trading day {trading_day}: existing {existing_msg_id} vs new {message_id}")
            
            if DUPLICATE_POLICY == "skip":
                logger.info(f"Policy 'skip': Ignoring duplicate message {message_id}")
                return "skip"
                
            elif DUPLICATE_POLICY == "allow":
                logger.info(f"Policy 'allow': Processing duplicate message {message_id} with flag")
                # Could add a revision flag here if needed
                return "proceed"
                
            elif DUPLICATE_POLICY == "replace":
                # Default timestamp if not provided
                if message_timestamp is None:
                    message_timestamp = datetime.now()
                
                # Check if new message should replace existing
                if self.store.should_replace(existing_details, message_id, message_timestamp, len(message_content)):
                    logger.info(f"Policy 'replace': New message {message_id} is newer and longer, replacing existing {existing_msg_id}")
                    # Delete existing setups for this trading day
                    deleted_count = self.store.delete_setups_for_trading_day(trading_day)
                    logger.info(f"Deleted {deleted_count} existing setups for trading day {trading_day}")
                    return "replaced"
                else:
                    logger.info(f"Policy 'replace': Existing message {existing_msg_id} is preferred, skipping new {message_id}")
                    return "skip"
            
            else:
                logger.warning(f"Unknown duplicate policy '{DUPLICATE_POLICY}', defaulting to proceed")
                return "proceed"
                
        except Exception as e:
            logger.error(f"Error in duplicate detection for message {message_id}: {e}")
            return "proceed"  # Default to processing on error

    def should_parse_message(self, content: str) -> bool:
        """
        Determine if a message should be parsed for trading setups.
        
        Args:
            content: Message content to check
            
        Returns:
            True if message appears to be an A+ scalp setup message
        """
        if not content or not isinstance(content, str):
            return False
            
        # Use the A+ parser's validation method
        return self.aplus_parser.validate_message(content)
    
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

def get_parsing_service(app=None) -> ParsingService:
    """Get the global parsing service instance."""
    global _service
    if _service is None:
        _service = ParsingService(app=app)
    return _service

def start_parsing_service(app=None):
    """Start the parsing service."""
    service = get_parsing_service(app=app)
    service.start_service()
    return service

def stop_parsing_service():
    """Stop the parsing service."""
    service = get_parsing_service()
    service.stop_service()