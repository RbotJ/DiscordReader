"""
A+ Scalp Setups Parser

Specialized parser for A+ scalp trading setup messages.
Extracts structured trading data from formatted Discord messages.
"""
import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, NamedTuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class APlusSetupDTO(NamedTuple):
    """Data transfer object for A+ parsed setup."""
    ticker: str
    setup_type: str
    profile_name: str  # RejectionNear, AggressiveBreakdown, etc.
    direction: str  # bullish, bearish
    strategy: str  # aggressive, conservative, rejection, bounce
    trigger_level: float  # Primary entry price
    target_prices: List[float]
    entry_condition: str  # Structured trigger logic
    raw_line: str


class APlusMessageParser:
    """
    Parser specifically designed for A+ scalp trading setup messages.
    Handles the structured format with emoji indicators and price arrays.
    """
    
    def __init__(self):
        """Initialize A+ parser with specific patterns."""
        # Message validation patterns - flexible to match actual format
        self.header_pattern = re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)', re.IGNORECASE)
        
        # Ticker section pattern (matches plain TICKER format, not **TICKER**)
        self.ticker_pattern = re.compile(r'^([A-Z]{2,5})\s*$', re.MULTILINE)
        
        # Setup line patterns matching actual A+ message format
        self.setup_patterns = {
            'aggressive_breakdown': re.compile(r'🔻\s*Aggressive\s+Breakdown\s+Below\s+([0-9.]+)\s+🔻\s+([\d.,\s]+)', re.IGNORECASE),
            'conservative_breakdown': re.compile(r'🔻\s*Conservative\s+Breakdown\s+Below\s+([0-9.]+)\s+🔻\s+([\d.,\s]+)', re.IGNORECASE),
            'aggressive_breakout': re.compile(r'🔼\s*Aggressive\s+Breakout\s+Above\s+([0-9.]+)\s+🔼\s+([\d.,\s]+)', re.IGNORECASE),
            'conservative_breakout': re.compile(r'🔼\s*Conservative\s+Breakout\s+Above\s+([0-9.]+)\s+🔼\s+([\d.,\s]+)', re.IGNORECASE),
            'bounce_zone': re.compile(r'🔄\s*Bounce\s+(?:Zone:?\s*|From\s+)([0-9.]+)(?:[-–]([0-9.]+))?\s+🔼\s+(?:Target:?\s*)?([^⚠️\n]+)', re.IGNORECASE),
            'rejection_near': re.compile(r'❌\s*Rejection\s+(?:Short\s+)?Near\s+([0-9.]+)\s+🔻\s+([\d.,\s]+)', re.IGNORECASE)
        }
        
        # Bias pattern
        self.bias_pattern = re.compile(r'⚠️\s*Bias\s*[—-]\s*(.+?)(?=\n\n|\n[A-Z]{2,5}\n|$)', re.IGNORECASE | re.DOTALL)
        
        # Month mapping for date parsing
        self.month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
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
            # Look for date patterns after the header:
            # Format 1: "A+ Scalp Trade Setups — Jun 2"
            # Format 2: "A+ Scalp Trade Setups — Thursday May 29"
            date_patterns = [
                re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)\s*[—-]\s*([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE),
                re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)\s*[—-]\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+([A-Za-z]+)\s+(\d{1,2})', re.IGNORECASE)
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
            
            logger.info(f"Extracted trading date: {trading_date} from '{month_name} {day}'")
            return trading_date
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing trading date: {e}")
            return None

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

    def parse_ticker_section(self, ticker: str, section_content: str) -> Tuple[List[APlusSetupDTO], Optional[str]]:
        """
        Parse all setups for a single ticker.
        
        Args:
            ticker: Stock ticker symbol
            section_content: Content for this ticker section
            
        Returns:
            Tuple of (list of setups, bias note)
        """
        setups = []
        bias_note = None
        
        # Extract bias first
        bias_match = self.bias_pattern.search(section_content)
        if bias_match:
            bias_note = bias_match.group(1).strip()
        
        # Parse each line individually to create separate setups
        lines = section_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('⚠️'):  # Skip empty lines and bias lines
                continue
            
            # Try to match this line against each setup pattern
            setup_created = False
            for setup_key, pattern in self.setup_patterns.items():
                match = pattern.search(line)
                
                if match:
                    try:
                        if setup_key == 'bounce_zone':
                            # Handle bounce zone with range
                            entry_low = float(match.group(1))
                            entry_high = float(match.group(2)) if match.group(2) else entry_low
                            targets = self.extract_price_list(match.group(3))
                            
                            setup = APlusSetupDTO(
                                ticker=ticker,
                                setup_type='bounce',
                                profile_name='BounceZone',
                                direction='bullish',
                                strategy='zone',
                                trigger_level=(entry_low + entry_high) / 2,
                                target_prices=targets,
                                entry_condition=f"Price drops to {entry_low}-{entry_high} zone and bounces",
                                raw_line=line
                            )
                            setups.append(setup)
                            setup_created = True
                            
                        else:
                            # Handle standard setups (breakdown, breakout, rejection)
                            trigger_price = float(match.group(1))
                            targets = self.extract_price_list(match.group(2))
                            
                            # Determine direction and strategy
                            if 'breakdown' in setup_key or 'rejection' in setup_key:
                                direction = 'bearish'
                            else:
                                direction = 'bullish'
                                
                            if 'aggressive' in setup_key:
                                strategy = 'aggressive'
                            elif 'conservative' in setup_key:
                                strategy = 'conservative'
                            elif 'rejection' in setup_key:
                                strategy = 'rejection'
                            else:
                                strategy = 'standard'
                            
                            # Map setup types and profile names
                            if 'breakdown' in setup_key:
                                setup_type = 'breakdown'
                                if 'aggressive' in setup_key:
                                    profile_name = 'AggressiveBreakdown'
                                    entry_condition = f"5-min candle close below {trigger_price} with volume confirmation"
                                else:
                                    profile_name = 'ConservativeBreakdown'
                                    entry_condition = f"Price creeps below {trigger_price} with sustained bearish momentum"
                            elif 'breakout' in setup_key:
                                setup_type = 'breakout'
                                if 'aggressive' in setup_key:
                                    profile_name = 'AggressiveBreakout'
                                    entry_condition = f"5-min candle close above {trigger_price} with volume confirmation"
                                else:
                                    profile_name = 'ConservativeBreakout'
                                    entry_condition = f"Price creeps above {trigger_price} with sustained bullish momentum"
                            elif 'rejection' in setup_key:
                                setup_type = 'rejection'
                                profile_name = 'RejectionNear'
                                entry_condition = f"Price pokes to {trigger_price} then reverses sharply away"
                            else:
                                setup_type = 'other'
                                profile_name = 'Unknown'
                                entry_condition = f"Monitor price action near {trigger_price}"
                            
                            setup = APlusSetupDTO(
                                ticker=ticker,
                                setup_type=setup_type,
                                profile_name=profile_name,
                                direction=direction,
                                strategy=strategy,
                                trigger_level=trigger_price,
                                target_prices=targets,
                                entry_condition=entry_condition,
                                raw_line=line
                            )
                            setups.append(setup)
                            setup_created = True
                        
                        break  # Stop checking other patterns for this line
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing line '{line}' for {ticker}: {e}")
                        continue
            
            # If no pattern matched, log the unrecognized line
            if not setup_created and line.strip():
                logger.debug(f"Unrecognized setup line for {ticker}: '{line}'")
        
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
        
        for ticker, section_content in ticker_sections.items():
            setups, bias_note = self.parse_ticker_section(ticker, section_content)
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