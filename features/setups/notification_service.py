"""
Setup Notification Service

This module provides services for notifying about trading setups via Discord.
"""
import logging
from datetime import datetime
from typing import List, Optional

from common.db import db
from features.setups.models import SetupMessage, TickerSetup, Signal, Bias
from features.discord.notification import (
    notify_new_setup_message,
    notify_signal_detected,
    notify_error
)

logger = logging.getLogger(__name__)

def process_new_setup_message(setup_message_id: int, test_mode: bool = False) -> bool:
    """
    Process a new setup message and send notifications.
    
    Args:
        setup_message_id: ID of the setup message
        test_mode: Whether to send to test channel
        
    Returns:
        Success status
    """
    try:
        # Get the setup message
        setup_message = SetupMessage.query.get(setup_message_id)
        if not setup_message:
            logger.error(f"Setup message not found: {setup_message_id}")
            return False
        
        # Send notification about the new setup message
        notify_new_setup_message(setup_message, test_mode)
        
        # Query directly to ensure we get the proper collection
        ticker_setups = TickerSetup.query.filter_by(setup_id=setup_message.id).all()
        
        # Process signals for each ticker setup
        for ticker_setup in ticker_setups:
            signals = Signal.query.filter_by(ticker_setup_id=ticker_setup.id).all()
            
            # Notify about each signal
            for signal in signals:
                notify_signal_detected(signal, test_mode)
        
        return True
    except Exception as e:
        logger.error(f"Error processing setup message {setup_message_id}: {e}")
        notify_error("Setup Processing", f"Failed to process setup message {setup_message_id}: {str(e)}", test_mode)
        return False

def get_recent_signals(limit: int = 5) -> List[Signal]:
    """
    Get recent signals from the database.
    
    Args:
        limit: Maximum number of signals to return
        
    Returns:
        List of signals
    """
    try:
        # Query signals ordered by creation date
        signals = Signal.query.order_by(Signal.created_at.desc()).limit(limit).all()
        return signals
    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        return []

def get_signals_by_symbol(symbol: str, limit: int = 10) -> List[Signal]:
    """
    Get signals for a specific symbol.
    
    Args:
        symbol: Ticker symbol
        limit: Maximum number of signals to return
        
    Returns:
        List of signals for the symbol
    """
    try:
        # Query signals for the ticker setup with the given symbol
        signals = (Signal.query
                  .join(TickerSetup, Signal.ticker_setup_id == TickerSetup.id)
                  .filter(TickerSetup.symbol == symbol)
                  .order_by(Signal.created_at.desc())
                  .limit(limit)
                  .all())
        return signals
    except Exception as e:
        logger.error(f"Error getting signals for symbol {symbol}: {e}")
        return []