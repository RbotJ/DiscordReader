"""
Message Parser Module

This module provides utility functions for parsing trade setup messages
and extracting ticker setups from various message formats.
"""
import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

def parse_setup_message(message: str) -> Dict[str, Any]:
    """
    Parse a setup message and extract relevant information.
    
    Args:
        message: The raw message text to parse
        
    Returns:
        Dict containing parsed data including tickers, dates, and setup details
    """
    from .setup_parser import SetupParser
    parser = SetupParser()
    return parser.parse_message(message)

def extract_ticker_setups(message: str) -> List[Dict[str, Any]]:
    """
    Extract ticker-specific setup information from a message.
    
    Args:
        message: The raw message text to parse
        
    Returns:
        List of dictionaries containing ticker setup details
    """
    parsed_data = parse_setup_message(message)
    return parsed_data.get('setups', [])

def normalize_ticker_symbol(ticker: str) -> str:
    """
    Normalize a ticker symbol to a standard format.
    
    Args:
        ticker: The ticker symbol to normalize
        
    Returns:
        The normalized ticker symbol
    """
    # Remove any special characters or whitespace
    ticker = re.sub(r'[^A-Z0-9]', '', ticker.upper())
    
    # Special case for indices
    if ticker.startswith('SPX'):
        return 'SPX'
    if ticker == 'SPY500' or ticker == 'SP500':
        return 'SPY'
    if ticker == 'QQQ100' or ticker == 'QQ100':
        return 'QQQ'
    if ticker == 'DJI' or ticker == 'DOWJONES':
        return 'DIA'
    
    return ticker