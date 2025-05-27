"""
Setup Parser Module

This module provides utilities for parsing trade setup messages
from different sources and formats.
"""
from typing import Dict, List, Optional, Any, Union

from .setup_parser import SetupParser
from .message_parser import parse_setup_message, extract_ticker_setups, normalize_ticker_symbol

__all__ = [
    'SetupParser',
    'parse_setup_message',
    'extract_ticker_setups',
    'normalize_ticker_symbol'
]