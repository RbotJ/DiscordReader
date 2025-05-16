"""
Setup Service Module

This module provides service functions for handling trading setups,
including persistence, retrieval, and business logic.
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union

from features.setups.setup_adapter import SetupAdapter
from common.models import TradeSetupMessage

# Configure logger
logger = logging.getLogger(__name__)

class SetupService:
    """Service for handling trading setups."""
    
    @staticmethod
    def save_setup(setup_message: TradeSetupMessage) -> Optional[int]:
        """
        Save a parsed setup message to the database.
        
        Args:
            setup_message: The parsed setup message object
            
        Returns:
            Optional[int]: ID of the saved message or None if error
        """
        return SetupAdapter.save_setup_message(setup_message)
    
    @staticmethod
    def get_setup_by_id(setup_id: int) -> Optional[Dict]:
        """
        Get a setup message by ID with all related data.
        
        Args:
            setup_id: The ID of the setup message
            
        Returns:
            Optional[Dict]: Setup message data as dictionary or None if not found
        """
        return SetupAdapter.get_setup_by_id(setup_id)
    
    @staticmethod
    def get_recent_setups(limit: int = 10, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get recent setup messages with optional filtering by ticker symbol.
        
        Args:
            limit: Maximum number of setups to return
            symbol: Optional ticker symbol to filter by
            
        Returns:
            List[Dict]: List of setup messages
        """
        return SetupAdapter.get_recent_setups(limit=limit, symbol=symbol)
    
    @staticmethod
    def get_setups_by_symbol(symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get setup messages for a specific ticker symbol.
        
        Args:
            symbol: Ticker symbol to filter by
            limit: Maximum number of setups to return
            
        Returns:
            List[Dict]: List of ticker setups for the specified symbol
        """
        return SetupAdapter.get_setups_by_symbol(symbol=symbol, limit=limit)