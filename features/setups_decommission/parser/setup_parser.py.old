"""
Setup Parser Base Class

This module provides a base class for parsing trade setup messages
from various sources and formats.
"""
import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class SetupParser:
    """
    Base class for parsing trade setup messages from various sources.
    
    This class provides methods to extract ticker symbols, setup details,
    and other metadata from setup messages.
    """
    
    def __init__(self):
        """Initialize the setup parser."""
        self.date_pattern = re.compile(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})?', re.IGNORECASE)
        self.ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        self.price_pattern = re.compile(r'(?:near|at|around|above|below|resistance|support)\s+\$?(\d+(?:\.\d+)?)')
    
    def parse_message(self, message: str) -> Dict[str, Any]:
        """
        Parse a setup message and extract relevant information.
        
        Args:
            message: The raw message text to parse
            
        Returns:
            Dict containing parsed data including tickers, dates, and setup details
        """
        logger.debug(f"Parsing message: {message[:100]}...")
        
        # Initialize result structure
        result = {
            'raw_text': message,
            'parsed_date': self._extract_date(message),
            'tickers': self._extract_tickers(message),
            'setups': [],
        }
        
        # Extract individual ticker setups
        for ticker in result['tickers']:
            setup = self._extract_ticker_setup(message, ticker)
            if setup:
                result['setups'].append(setup)
        
        return result
    
    def _extract_date(self, message: str) -> Optional[date]:
        """
        Extract the date from the message.
        
        Args:
            message: The message text
            
        Returns:
            Extracted date or None if not found
        """
        match = self.date_pattern.search(message)
        if match:
            day = int(match.group(1))
            year = int(match.group(2)) if match.group(2) else datetime.now().year
            month_str = match.group(0).split()[1]
            
            # Map month string to number
            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            
            month = months.get(month_str.lower()[:3], datetime.now().month)
            
            try:
                return date(year, month, day)
            except ValueError:
                logger.warning(f"Invalid date extracted: {year}-{month}-{day}")
                return None
        
        # If no date found, use current date
        return datetime.now().date()
    
    def _extract_tickers(self, message: str) -> List[str]:
        """
        Extract ticker symbols from the message.
        
        Args:
            message: The message text
            
        Returns:
            List of ticker symbols
        """
        # Get all potential tickers
        matches = self.ticker_pattern.findall(message)
        
        # Filter out common words that might be mistaken for tickers
        common_words = {'A', 'I', 'AT', 'BE', 'DO', 'GO', 'IN', 'IT', 'ME', 'ON', 'OR', 'SO', 'TO', 'UP', 'US', 'WE'}
        tickers = [ticker for ticker in matches if ticker not in common_words]
        
        # Remove duplicates while preserving order
        unique_tickers = []
        for ticker in tickers:
            if ticker not in unique_tickers:
                unique_tickers.append(ticker)
        
        return unique_tickers
    
    def _extract_ticker_setup(self, message: str, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Extract setup details for a specific ticker.
        
        Args:
            message: The message text
            ticker: The ticker symbol to extract setup for
            
        Returns:
            Dict with setup details or None if no setup found
        """
        # Find sections of the message that might refer to this ticker
        ticker_index = message.find(ticker)
        if ticker_index == -1:
            return None
        
        # Get the part of the message after the ticker mention
        ticker_context = message[ticker_index:ticker_index + 200]
        
        # Extract price level if available
        price_match = self.price_pattern.search(ticker_context)
        price = float(price_match.group(1)) if price_match else None
        
        # Determine setup type based on keywords
        setup_type = 'unknown'
        if 'bullish' in ticker_context.lower():
            setup_type = 'bullish'
        elif 'bearish' in ticker_context.lower():
            setup_type = 'bearish'
        elif 'resistance' in ticker_context.lower():
            setup_type = 'resistance'
        elif 'support' in ticker_context.lower():
            setup_type = 'support'
        elif 'breakout' in ticker_context.lower():
            setup_type = 'breakout'
        elif 'breakdown' in ticker_context.lower():
            setup_type = 'breakdown'
        
        return {
            'ticker': ticker,
            'price': price,
            'setup_type': setup_type,
            'context': ticker_context.strip()
        }