"""
Parsing Feature Module

Vertical slice for parsing Discord messages into trade setups.
Provides a complete, self-contained parsing system.
"""

from .service import get_parsing_service, start_parsing_service, stop_parsing_service
from .parser import MessageParser, ParsedSetupDTO, ParsedLevelDTO
from .models import TradeSetup, ParsedLevel
from .store import get_parsing_store
from .listener import get_parsing_listener

__all__ = [
    'get_parsing_service',
    'start_parsing_service', 
    'stop_parsing_service',
    'MessageParser',
    'ParsedSetupDTO',
    'ParsedLevelDTO',
    'TradeSetup',
    'ParsedLevel',
    'get_parsing_store',
    'get_parsing_listener'
]