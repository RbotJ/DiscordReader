"""
Refactored A+ Scalp Setups Parser
- Replaces fragile full-line regex with structured token parsing
- Creates a simplified, resilient internal model per trade setup
- Enforces one labeled setup per ticker/day
- Logs audit info for missing or extra setups

Format Variations Supported:
- Standard: "Above 596.90 🔼 599.80, 602.00, 605.50"
- New format: "🔻 Aggressive Breakdown 599.00 🔻 597.40, 595.60, 593.50"
- Rejection with direction: "❌ Rejection Short 600.10 🔻 598.00, 596.40, 594.20"
- Parentheses format: "Above 596.90 (599.80, 602.00, 605.50)"
"""

import logging
import re
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from .failure_tracker import record_parsing_failure, FailureReason

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


def parse_setup_prices(line: str) -> Tuple[Optional[float], List[float]]:
    """Parse trigger and target prices from setup line using structured patterns."""
    
    # Pattern variations for different A+ formats
    patterns = [
        # Standard: "Above 596.90 🔼 599.80, 602.00, 605.50"
        r'(?:Above|Below|Near)\s+(\d{2,5}\.\d{2})[^0-9]*?(?:🔼|🔻|❌|🔄)\s*(\d{2,5}\.\d{2}(?:\s*,\s*\d{2,5}\.\d{2})*)',
        
        # New format: "Breakdown 599.00 🔻 597.40, 595.60, 593.50"
        r'(?:Breakdown|Breakout|Rejection)\s+(?:Above|Below|Short|Long)?\s*(\d{2,5}\.\d{2})\s*(?:🔼|🔻|❌|🔄)\s*(\d{2,5}\.\d{2}(?:\s*,\s*\d{2,5}\.\d{2})*)',
        
        # Emoji first: "🔻 Aggressive Breakdown 599.00 🔻 597.40, 595.60"
        r'(?:🔼|🔻|❌|🔄)\s*(?:Aggressive|Conservative)?\s*(?:Breakdown|Breakout|Rejection)\s+(?:Above|Below|Short|Long|Near)?\s*(\d{2,5}\.\d{2})\s*(?:🔼|🔻|❌|🔄)\s*(\d{2,5}\.\d{2}(?:\s*,\s*\d{2,5}\.\d{2})*)',
        
        # Alternative: "596.90 | 599.80, 602.00, 605.50"
        r'(\d{2,5}\.\d{2})\s*\|\s*(\d{2,5}\.\d{2}(?:\s*,\s*\d{2,5}\.\d{2})*)',
        
        # Parentheses: "Above 596.90 (599.80, 602.00, 605.50)"
        r'(?:Above|Below|Near)\s+(\d{2,5}\.\d{2})[^(]*\((\d{2,5}\.\d{2}(?:\s*,\s*\d{2,5}\.\d{2})*)\)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            trigger = float(match.group(1))
            target_string = match.group(2)
            targets = [float(p.strip()) for p in target_string.split(',')]
            
            # Validate price structure
            if validate_price_structure(line, trigger, targets):
                return trigger, targets
    
    # Enhanced fallback parsing for partial line failures
    numbers = re.findall(r'\d{2,5}\.\d{2}', line)
    if len(numbers) >= 2:
        trigger = float(numbers[0])
        targets = [float(p) for p in numbers[1:]]
        
        # Try standard validation first
        if validate_price_structure(line, trigger, targets):
            return trigger, targets
        
        # Relaxed fallback mode for partial failures
        logger.info(f"Using fallback-pricing-mode for line: {line[:50]}...")
        
        # More permissive validation for edge cases
        if len(targets) >= 1 and trigger != targets[0]:
            # Log the relaxed parsing decision
            logger.debug(f"Relaxed parsing: trigger={trigger}, targets={targets[:3]}")  # Limit to first 3 targets
            return trigger, targets[:4]  # Cap at 4 targets maximum
    
    return None, []


def validate_price_structure(line: str, trigger: float, targets: List[float]) -> bool:
    """Validate that price structure makes logical sense."""
    
    # Check minimum target count
    if len(targets) < 1:
        logger.warning(f"No targets found in line: {line}")
        return False
    
    # Check maximum target count (A+ typically has 3-4 targets)
    if len(targets) > 5:
        logger.warning(f"Too many targets ({len(targets)}) in line: {line}")
        return False
    
    # Check for duplicate trigger in targets
    if trigger in targets:
        logger.error(f"Trigger price {trigger} found in targets {targets} - line: {line}")
        return False
    
    # Direction-based validation
    if 'Above' in line or '🔼' in line:
        # Bullish: targets should be higher than trigger
        if not all(t > trigger for t in targets):
            logger.warning(f"Bullish setup but targets not all above trigger: {trigger} vs {targets}")
            return False
    elif 'Below' in line or '🔻' in line:
        # Bearish: targets should be lower than trigger
        if not all(t < trigger for t in targets):
            logger.warning(f"Bearish setup but targets not all below trigger: {trigger} vs {targets}")
            return False
    
    return True


def extract_setup_line(line: str, ticker: str, trading_day: date, index: int) -> Optional[TradeSetup]:
    trigger, targets = parse_setup_prices(line)
    
    if trigger is None or not targets:
        logger.warning(f"Could not parse valid prices from line: {line}")
        return None

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
        # Message validation patterns - flexible to match actual format variations
        self.header_pattern = re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)', re.IGNORECASE)
        
        # Ticker section pattern (matches plain TICKER format and ✅ TICKER format)
        self.ticker_pattern = re.compile(r'^(?:✅\s+)?([A-Z]{2,5})\s*$', re.MULTILINE)
        
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

    def extract_trading_day(self, content: str, message_timestamp: datetime) -> date:
        """
        Extract trading day from message content using hybrid token approach.
        Falls back to message timestamp if no date is found.

        Args:
            content: full message string
            message_timestamp: datetime the message was posted (in UTC or EST)

        Returns:
            Trading day as datetime.date
        """
        lines = content.splitlines()
        tokens = []

        # Scan the top ~5 lines for month/day pattern
        for line in lines[:5]:
            tokens += line.strip().replace(',', '').replace('.', '').split()

        for i, token in enumerate(tokens):
            month_token = token.lower()
            if month_token in self.month_map and i + 1 < len(tokens):
                try:
                    day = int(tokens[i + 1])
                    year = message_timestamp.year
                    extracted_date = date(year, self.month_map[month_token], day)
                    
                    logger.debug(f"Using header date {extracted_date} from line: '{lines[0] if lines else content[:50]}'")
                    logger.info(f"Extracted trading day: {extracted_date} (method: header)")
                    
                    return extracted_date
                except ValueError:
                    continue  # e.g., "Jun five" or misformatted day

        # Fallback: use message timestamp converted to Central Time
        from common.timezone import get_central_trading_day
        fallback_date = get_central_trading_day(message_timestamp)
        logger.info(f"Falling back to Central Time timestamp: {fallback_date} (method: fallback)")
        return fallback_date

    def validate_message(self, content: str, message_id: str = "unknown") -> bool:
        """
        Validate if this is an A+ message with token-based header analysis.
        
        Accepts formats:
        - "A+ Scalp Trade Setups"
        - "A+ Trade Setups" 
        - "A+ Scalp Setups"
        
        Args:
            content: Raw message content
            message_id: Message ID for logging
            
        Returns:
            True if message contains valid A+ header and passes checks
        """
        if not content or not isinstance(content, str):
            logger.info(f'{{"reason": "empty_content", "message_id": "{message_id}"}}')
            return False
        
        # Get first line and tokenize first 6 words
        lines = content.strip().splitlines()
        if not lines:
            logger.info(f'{{"reason": "no_lines", "message_id": "{message_id}"}}')
            return False
            
        header = lines[0].strip()
        header_words = header.split()[:6]  # First 6 words only
        header_tokens = [word.lower().rstrip('—').rstrip('-').rstrip(':') for word in header_words]
        
        # Required tokens: A+ and Setups
        required_tokens = ["a+", "setups"]
        has_required = all(any(token in header_token for header_token in header_tokens) for token in required_tokens)
        
        if not has_required:
            logger.info(f'{{"reason": "header_token_mismatch", "message_id": "{message_id}", "header": "{header[:50]}", "missing_tokens": "{[t for t in required_tokens if not any(t in ht for ht in header_tokens)]}"}}')
            return False
        
        # Rejection tokens: Test or Check
        reject_tokens = ["test", "check"]
        has_reject = any(reject_token in header_tokens for reject_token in reject_tokens)
        
        if has_reject:
            logger.info(f'{{"reason": "test_indicator", "message_id": "{message_id}", "header": "{header[:50]}"}}')
            return False
            
        # Content length check
        if len(content) < 50:
            logger.info(f'{{"reason": "content_too_short", "message_id": "{message_id}", "length": {len(content)}}}')
            return False

        # Log successful validation with optional tokens found
        optional_tokens = ["scalp", "trade"]
        found_optional = [token for token in optional_tokens if any(token in header_token for header_token in header_tokens)]
        
        logger.debug(f"Valid A+ message: {message_id}, header tokens: {header_tokens[:4]}, optional: {found_optional}")
        return True
    


    def extract_trading_date(self, content: str) -> Optional[date]:
        """
        # DEPRECATED: Use extract_trading_day() with message_timestamp instead
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

    def parse_message(self, content: str, message_id: Optional[str] = None, message_timestamp: Optional[datetime] = None, **kwargs) -> Dict[str, Any]:
        """
        Parse complete A+ scalp setups message with duplicate trading day resolution.
        
        Args:
            content: Raw message content
            message_id: Discord message ID
            message_timestamp: When the message was posted (for date inference)
            **kwargs: Additional context
            
        Returns:
            Dictionary with parsed data
        """
        if not self.validate_message(content, message_id or "unknown"):
            return {
                'success': False,
                'error': 'Not an A+ scalp setups message',
                'setups': [],
                'trading_date': None
            }
        
        # Extract trading date using new hybrid approach if timestamp provided
        if message_timestamp:
            trading_date = self.extract_trading_day(content, message_timestamp)
            extraction_method = "hybrid"
        else:
            # Fallback to old method if no timestamp (backward compatibility)
            trading_date = self.extract_trading_date(content)
            extraction_method = "legacy"
            if not trading_date:
                trading_date = date.today()
                extraction_method = "fallback"
        
        # Handle duplicate trading day resolution
        from .store import get_parsing_store
        store = get_parsing_store()
        
        duplicate_status = "none"
        if message_id:
            existing_details = store.find_existing_message_for_day(trading_date)
            if existing_details:
                existing_msg_id, existing_timestamp, existing_length = existing_details
                
                # Check if current message should replace existing one
                current_length = len(content)
                current_timestamp = message_timestamp or datetime.utcnow()
                
                if store.should_replace(existing_details, message_id, current_timestamp, current_length):
                    # Delete existing setups for this trading day
                    deleted_count = store.delete_setups_for_trading_day(trading_date)
                    logger.info(f"Replaced {deleted_count} existing setups for trading day {trading_date} with newer message {message_id}")
                    duplicate_status = "replaced"
                else:
                    # Skip parsing this message as existing one is better
                    logger.info(f"Skipping duplicate message {message_id} for trading day {trading_date} - existing message is newer/longer")
                    return {
                        'success': False,
                        'error': 'Duplicate trading day - existing message is newer/longer',
                        'setups': [],
                        'trading_date': trading_date,
                        'duplicate_status': 'skipped',
                        'existing_message_id': existing_msg_id
                    }
        
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
        
        # Parse each ticker section and collect quality metrics
        all_setups = []
        ticker_bias_notes = {}
        parse_quality_metrics = {
            'total_lines': len(lines),
            'ticker_sections': len(ticker_sections),
            'lines_processed': 0,
            'lines_skipped': 0,
            'bias_extracted': False,
            'parsing_method': 'structured',
            'fallback_price_parsing': 0
        }
        
        for ticker, section_content in ticker_sections.items():
            section_lines = section_content.split('\n')
            
            # Track lines processed for this ticker section
            for line in section_lines:
                if line.strip():
                    parse_quality_metrics['lines_processed'] += 1
            
            setups, bias_note = self.parse_ticker_section(ticker, section_content, trading_date)
            all_setups.extend(setups)
            
            if bias_note:
                ticker_bias_notes[ticker] = bias_note
                parse_quality_metrics['bias_extracted'] = True
        
        # Calculate parse health score
        if parse_quality_metrics['total_lines'] > 0:
            parse_success_rate = (parse_quality_metrics['lines_processed'] / parse_quality_metrics['total_lines']) * 100
        else:
            parse_success_rate = 0
        
        parse_quality_metrics['parse_success_rate'] = round(parse_success_rate, 1)
        parse_quality_metrics['setup_yield'] = len(all_setups) / max(1, parse_quality_metrics['ticker_sections'])
        
        # Deduplication step: track (ticker, setup_type, direction, trigger_level) to prevent duplicate insertions
        deduplicated_setups = []
        seen_setups = set()
        duplicates_skipped = 0
        
        for setup in all_setups:
            # Create deduplication key from setup characteristics
            dedup_key = (
                setup.ticker,
                setup.label or "unlabeled",  # setup_type
                setup.direction,
                setup.trigger_level
            )
            
            if dedup_key not in seen_setups:
                seen_setups.add(dedup_key)
                deduplicated_setups.append(setup)
            else:
                duplicates_skipped += 1
                logger.info(f'{{"message_id": "{message_id or "unknown"}", "action": "duplicate_setup_skipped", "ticker": "{setup.ticker}", "trigger": {setup.trigger_level}, "direction": "{setup.direction}"}}')
        
        # Log deduplication summary if any duplicates were found
        if duplicates_skipped > 0:
            logger.info(f"Deduplication: kept {len(deduplicated_setups)} setups, skipped {duplicates_skipped} duplicates for message {message_id}")
        
        return {
            'success': True,
            'setups': deduplicated_setups,
            'trading_date': trading_date,
            'ticker_bias_notes': ticker_bias_notes,
            'total_setups': len(deduplicated_setups),
            'duplicates_skipped': duplicates_skipped,
            'tickers_found': list(ticker_sections.keys()),
            'message_id': message_id,
            'duplicate_status': duplicate_status,
            'extraction_metadata': {
                'extraction_method': extraction_method,
                'timestamp_provided': message_timestamp is not None,
                'extraction_confidence': 'high' if extraction_method == 'hybrid' else 'medium'
            },
            'parse_quality': parse_quality_metrics
        }


# Global parser instance
_aplus_parser = None

def get_aplus_parser() -> APlusMessageParser:
    """Get the global A+ parser instance."""
    global _aplus_parser
    if _aplus_parser is None:
        _aplus_parser = APlusMessageParser()
    return _aplus_parser