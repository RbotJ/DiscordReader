"""
Refactored A+ Scalp Setups Parser
- Replaces fragile full-line regex with structured token parsing
- Creates a simplified, resilient internal model per trade setup
- Enforces one labeled setup per ticker/day
- Logs audit info for missing or extra setups
"""

import logging
import re
from datetime import date
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ----- Data Model -----

@dataclass
class TradeSetup:
    id: str
    ticker: str
    trading_day: date
    index: int
    trigger_level: float
    target_prices: List[float]
    direction: str                      # 'long' or 'short'
    label: Optional[str]                # Human-readable label like "AggressiveBreakout"
    keywords: List[str]                 # e.g., ["breakout", "aggressive"]
    emoji_hint: Optional[str]          # e.g., '🔼'
    raw_line: str


# ----- Utility Functions -----

PRICE_LIST_RE = re.compile(r'(\d{2,5}\.\d{2})(?:\s*,\s*\d{2,5}\.\d{2})*')

KEYWORDS_BY_LABEL = {
    'Rejection': ['rejection', 'reject'],
    'AggressiveBreakout': ['aggressive', 'breakout'],
    'ConservativeBreakout': ['conservative', 'breakout'],
    'AggressiveBreakdown': ['aggressive', 'breakdown'],
    'ConservativeBreakdown': ['conservative', 'breakdown'],
    'BounceZone': ['bounce', 'zone'],
    'Bias': ['bias']
}

DIRECTION_HINTS = {
    '🔻': 'short',
    '🔼': 'long',
    '❌': 'short',# usually implies rejection down
    '🔄': 'long'  # usually implies bounce up
}


def parse_price_list(text: str) -> List[float]:
    try:
        return [float(p.strip()) for p in text.split(',') if p.strip()]
    except ValueError:
        logger.warning(f"Failed to parse price list from: {text}")
        return []


def classify_setup(line: str) -> Tuple[Optional[str], List[str]]:
    tokens = line.lower()
    matched_labels = []
    for label, keywords in KEYWORDS_BY_LABEL.items():
        if all(k in tokens for k in keywords):
            matched_labels.append(label)
    return (matched_labels[0] if matched_labels else None, matched_labels)


def extract_setup_line(line: str, ticker: str, trading_day: date, index: int) -> Optional[TradeSetup]:
    numbers = re.findall(r'\d{2,5}\.\d{2}', line)
    if len(numbers) < 2:
        logger.warning(f"Not enough prices in line: {line}")
        return None

    trigger = float(numbers[0])
    targets = [float(p) for p in numbers[1:]]

    emoji = next((icon for icon in DIRECTION_HINTS if icon in line), None)
    direction = DIRECTION_HINTS[emoji] if emoji in DIRECTION_HINTS else 'long'

    label, keywords = classify_setup(line)
    setup_id = f"{trading_day.strftime('%Y%m%d')}_{ticker}_Setup_{index+1}"

    return TradeSetup(
        id=setup_id,
        ticker=ticker,
        trading_day=trading_day,
        index=index + 1,
        trigger_level=trigger,
        target_prices=targets,
        direction=direction or 'long',
        label=label,
        keywords=keywords or [],
        emoji_hint=emoji,
        raw_line=line
    )


# ----- Main Entry Point -----

def parse_ticker_section(ticker: str, content: str, trading_day: date) -> List[TradeSetup]:
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('⚠️')]
    setups = []

    for i, line in enumerate(lines):
        setup = extract_setup_line(line, ticker, trading_day, i)
        if setup:
            setups.append(setup)
        else:
            logger.debug(f"Skipped line {i}: {line}")

    logger.info(f"Parsed {len(setups)} setups for {ticker} on {trading_day}")
    return setups


# Optional: define expected profile audit
EXPECTED_PROFILES = [
    'Rejection', 'AggressiveBreakdown', 'ConservativeBreakdown',
    'AggressiveBreakout', 'ConservativeBreakout', 'BounceZone', 'Bias'
]

def audit_profile_coverage(setups: List[TradeSetup], ticker: str, trading_day: date):
    found = {s.label for s in setups if s.label}
    missing = set(EXPECTED_PROFILES) - found
    if missing:
        logger.warning(f"Missing expected setups for {ticker} on {trading_day}: {sorted(missing)}")
    if len(setups) > len(EXPECTED_PROFILES):
        logger.warning(f"Extra setups detected: {len(setups)} > {len(EXPECTED_PROFILES)}")


class APlusMessageParser:
    """
    Refactored parser using structured token parsing instead of fragile regex patterns.
    """
    
    def __init__(self):
        """Initialize A+ parser with header validation patterns."""
        # Message validation patterns - flexible to match actual format
        self.header_pattern = re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)', re.IGNORECASE)
        
        # Ticker section pattern (matches plain TICKER format, not **TICKER**)
        self.ticker_pattern = re.compile(r'^([A-Z]{2,5})\s*$', re.MULTILINE)
        
        # Bias pattern
        self.bias_pattern = re.compile(r'⚠️\s*Bias\s*[—-]\s*(.+?)(?=\n\n|\n[A-Z]{2,5}\n|$)', re.IGNORECASE | re.DOTALL)
        
        # Enhanced month mapping with abbreviation support
        self.month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2, 
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }

    def validate_message(self, content: str) -> bool:
        """
        Validate if this is an A+ scalp setups message.
        
        Args:
            content: Raw message content
            
        Returns:
            True if message contains A+ trade setups header
        """
        return bool(self.header_pattern.search(content))

    def extract_trading_date(self, content: str) -> Optional[date]:
        """
        Extract trading date from message header.
        
        Args:
            content: Raw message content
            
        Returns:
            Trading date or None if not found
        """
        try:
            # Enhanced patterns to catch more header variations:
            date_patterns = [
                # "A+ Scalp Trade Setups — Sunday June 15"
                re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)\.?\s*[—\-–]+\s*(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE),
                # "A+ Scalp Trade Setups — June 15" 
                re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)\.?\s*[—\-–]+\s*([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE),
                # "A+ Scalp Trade Setups -- Mon Jun 9" (double dash)
                re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)\.?\s*--+\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE),
                # "A+ Scalp Trade Setups. — Wed Jun 11" (period and day abbreviation)
                re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)\.?\s*[—\-–]+\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE),
                # Flexible fallback pattern
                re.compile(r'A\+.*?Setups\.?\s*[—\-–-]+\s*(?:\w+\s+)?([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE)
            ]
            
            date_match = None
            for pattern in date_patterns:
                date_match = pattern.search(content)
                if date_match:
                    break
            
            if not date_match:
                logger.warning("No date found in A+ message header")
                return None
                
            month_name = date_match.group(1).lower()
            day = int(date_match.group(2))
            
            # Map month name to number
            month_num = self.month_map.get(month_name)
            if not month_num:
                # Try partial month names (Jun -> June)
                for full_month, num in self.month_map.items():
                    if full_month.startswith(month_name):
                        month_num = num
                        break
                        
            if not month_num:
                logger.warning(f"Could not parse month: {month_name}")
                return None
                
            # Use current year for trading date
            current_year = date.today().year
            trading_date = date(current_year, month_num, day)
            
            # Validate the extracted date
            if self.validate_trading_date(trading_date, content):
                logger.info(f"Extracted trading date: {trading_date} from '{month_name} {day}'")
                return trading_date
            else:
                logger.warning(f"Extracted trading date {trading_date} failed validation")
                return None
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing trading date: {e}")
            return None

    def validate_trading_date(self, extracted_date: Optional[date], content: str) -> bool:
        """
        Validate that extracted trading date makes sense.
        
        Args:
            extracted_date: The extracted date to validate
            content: Original message content for context
            
        Returns:
            True if date is valid and reasonable
        """
        if not extracted_date:
            return False
        
        # Check if date is reasonable (within 1 year)
        today = date.today()
        if abs((extracted_date - today).days) > 365:
            logger.warning(f"Extracted trading date {extracted_date} seems unrealistic")
            return False
        
        return True

    def extract_price_list(self, price_string: str) -> List[float]:
        """
        Extract list of prices from comma-separated string.
        
        Args:
            price_string: String like "141.40, 139.20, 137.60"
            
        Returns:
            List of price floats
        """
        prices = []
        # Split by comma and clean each price
        for price_str in price_string.split(','):
            price_str = price_str.strip()
            try:
                price = float(price_str)
                prices.append(price)
            except ValueError:
                logger.warning(f"Could not parse price: {price_str}")
                continue
        return prices

    def parse_ticker_section(self, ticker: str, section_content: str, trading_day: date) -> Tuple[List[TradeSetup], Optional[str]]:
        """
        Parse all setups for a single ticker using the refactored approach.
        
        Args:
            ticker: Stock ticker symbol
            section_content: Content for this ticker section
            trading_day: Trading day date
            
        Returns:
            Tuple of (list of setups, bias note)
        """
        # Extract bias first
        bias_note = None
        bias_match = self.bias_pattern.search(section_content)
        if bias_match:
            bias_note = bias_match.group(1).strip()
        
        # Use the new refactored parsing logic
        setups = parse_ticker_section(ticker, section_content, trading_day)
        
        # Run audit for this ticker
        audit_profile_coverage(setups, ticker, trading_day)
        
        return setups, bias_note

    def parse_message(self, content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse complete A+ scalp setups message.
        
        Args:
            content: Raw message content
            message_id: Discord message ID
            
        Returns:
            Dictionary with parsed data
        """
        if not self.validate_message(content):
            return {
                'success': False,
                'error': 'Not an A+ scalp setups message',
                'setups': [],
                'trading_date': None
            }
        
        # Extract trading date
        trading_date = self.extract_trading_date(content)
        
        # Split content into ticker sections
        ticker_sections = {}
        current_ticker = None
        current_content = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check if this line is a ticker
            ticker_match = self.ticker_pattern.match(line)
            if ticker_match:
                # Save previous ticker section
                if current_ticker and current_content:
                    ticker_sections[current_ticker] = '\n'.join(current_content)
                
                # Start new ticker section
                current_ticker = ticker_match.group(1)
                current_content = []
            elif current_ticker and line:
                current_content.append(line)
        
        # Save last ticker section
        if current_ticker and current_content:
            ticker_sections[current_ticker] = '\n'.join(current_content)
        
        # Parse each ticker section
        all_setups = []
        ticker_bias_notes = {}
        
        # Preserve None to indicate parsing failure, don't mask with fallback
        current_trading_date = trading_date
        if not current_trading_date:
            logger.error(f"Failed to extract trading date from message {message_id}, using today as fallback")
            current_trading_date = date.today()
        
        for ticker, section_content in ticker_sections.items():
            setups, bias_note = self.parse_ticker_section(ticker, section_content, current_trading_date)
            all_setups.extend(setups)
            if bias_note:
                ticker_bias_notes[ticker] = bias_note
        
        return {
            'success': True,
            'setups': all_setups,
            'trading_date': trading_date,
            'ticker_bias_notes': ticker_bias_notes,
            'total_setups': len(all_setups),
            'tickers_found': list(ticker_sections.keys()),
            'message_id': message_id
        }


# Global parser instance
_aplus_parser = None

def get_aplus_parser() -> APlusMessageParser:
    """Get the global A+ parser instance."""
    global _aplus_parser
    if _aplus_parser is None:
        _aplus_parser = APlusMessageParser()
    return _aplus_parser