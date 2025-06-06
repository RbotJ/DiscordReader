"""
Parsing Service Module

Main service orchestrator for the parsing vertical slice.
Provides a unified interface for parsing functionality.
"""
import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional

from .parser import MessageParser
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