"""
Strategy Module

This module provides access to trading strategy components,
including signal detection and candle pattern detection.
"""
import logging
from typing import Dict, List, Any, Optional

from features.strategy.candle_detector import (
    init_candle_detector, 
    add_signal, 
    remove_signal, 
    get_active_signals,
    shutdown as _shutdown_candle_detector
)

logger = logging.getLogger(__name__)

def start_candle_detector() -> bool:
    """
    Start the candle detector.
    
    Returns:
        bool: Success status
    """
    return init_candle_detector()

def stop_candle_detector() -> bool:
    """
    Stop the candle detector.
    
    Returns:
        bool: Success status
    """
    return _shutdown_candle_detector()

def get_candle_signals(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get active candle signals.
    
    Args:
        symbol: Optional ticker symbol filter
        
    Returns:
        List of signal dictionaries
    """
    return get_active_signals(symbol)

def add_candle_signal(signal_data: Dict[str, Any]) -> bool:
    """
    Add a candle signal to be monitored.
    
    Args:
        signal_data: Signal data dictionary
        
    Returns:
        bool: Success status
    """
    return add_signal(signal_data)

def remove_candle_signal(signal_id: str) -> bool:
    """
    Remove a candle signal by ID.
    
    Args:
        signal_id: Signal ID to remove
        
    Returns:
        bool: Success status
    """
    return remove_signal(signal_id)