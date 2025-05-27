"""
Parsing Rules Module

Contains A+ trading logic and rules for parsing Discord messages.
This module implements specific business rules for identifying conservative shorts,
aggressive longs, and other A+ trading patterns from message content.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
import re
from enum import Enum

logger = logging.getLogger(__name__)

# Enhanced signal extraction patterns from legacy setups parser
SIGNAL_PATTERNS = {
    "breakout": [
        r'\b(?:breakout|break out|breaking out|breaking)\s+(?:above|over|past)\s+(\d+(?:\.\d+)?)',
        r'\[BREAKOUT\].*?(?:above|over|past)\s+(\d+(?:\.\d+)?)',
        r'(?:buying|long|calls)\s+(?:above|over|past)\s+(\d+(?:\.\d+)?)',
        r'(?:aggressive|conservative)\s+breakout\s+(?:above|over|past)\s+(\d+(?:\.\d+)?)'
    ],
    "breakdown": [
        r'\b(?:breakdown|break down|breaking down)\s+(?:below|under|beneath)\s+(\d+(?:\.\d+)?)',
        r'\[BREAKDOWN\].*?(?:below|under|beneath)\s+(\d+(?:\.\d+)?)',
        r'(?:selling|short|puts)\s+(?:below|under|beneath)\s+(\d+(?:\.\d+)?)',
        r'(?:aggressive|conservative)\s+breakdown\s+(?:below|under|beneath)\s+(\d+(?:\.\d+)?)'
    ],
    "rejection": [
        r'\b(?:rejection|reject|rejecting)\s+(?:near|at|around)\s+(\d+(?:\.\d+)?)',
        r'\[REJECTION\].*?(?:near|at|around)\s+(\d+(?:\.\d+)?)',
        r'(?:resistance|support)\s+(?:rejection|reject)\s+(?:near|at|around)\s+(\d+(?:\.\d+)?)'
    ],
    "bounce": [
        r'\b(?:bounce|bouncing|support)\s+(?:from|off|at)\s+(\d+(?:\.\d+)?)',
        r'\[BOUNCE\].*?(?:from|off|at)\s+(\d+(?:\.\d+)?)',
        r'(?:bullish|bearish)\s+bounce\s+(?:from|off|at)\s+(\d+(?:\.\d+)?)'
    ]
}

# Bias extraction patterns from legacy parser
BIAS_PATTERNS = [
    r'(?i)(?:remain|bias|sentiment|outlook|stance)\s+(bullish|bearish)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)',
    r'(?i)(bullish|bearish)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)',
    r'(?i)(bullish|bearish)\s+(?:bias|sentiment|outlook|stance)\s+(?:above|below|near)\s+(\d+(?:\.\d+)?)'
]

# Target extraction patterns from legacy parser
TARGET_PATTERNS = [
    r'(?i)(?:target|tgt|price target|take profit|tp)(?:\s+\d+)?:\s*(\d+(?:\.\d+)?)',
    r'(?i)(?:target|tgt|price target|take profit|tp)(?:\s+\d+)?\s+(?:at|is|of|near|around)?\s*(\d+(?:\.\d+)?)',
    r'(?i)(?:target|tgt|price target|take profit|tp)(?:\s+\d+)?[:\s]+(\d+(?:\.\d+)?)'
]

# Emoji mappings for signal categories
EMOJI_MAP = {
    # Breakout indicators
    "🔼": "[BREAKOUT]",
    "⬆️": "[BREAKOUT]",
    "🚀": "[BREAKOUT]",
    "🔝": "[BREAKOUT]",
    
    # Breakdown indicators
    "🔽": "[BREAKDOWN]",
    "⬇️": "[BREAKDOWN]",
    "📉": "[BREAKDOWN]",
    "🔻": "[BREAKDOWN]",
    
    # Rejection indicators
    "❌": "[REJECTION]",
    "🚫": "[REJECTION]",
    "🛑": "[REJECTION]",
    "⛔": "[REJECTION]",
    
    # Bounce indicators
    "🔄": "[BOUNCE]",
    "↩️": "[BOUNCE]",
    "↪️": "[BOUNCE]",
    "🔙": "[BOUNCE]"
}


class SetupAggressiveness(Enum):
    """Enum for setup aggressiveness levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TradingBias(Enum):
    """Enum for trading bias directions."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class APlusRulesEngine:
    """
    Implements A+ trading rules and pattern recognition.
    
    This class contains the specific business logic for identifying
    trading patterns that align with A+ trading methodology.
    """
    
    def __init__(self):
        """Initialize the rules engine with A+ specific patterns."""
        self.conservative_short_patterns = [
            r'conservative\s+short',
            r'safe\s+short',
            r'low\s+risk\s+short',
            r'confirmed\s+breakdown'
        ]
        
        self.aggressive_long_patterns = [
            r'aggressive\s+long',
            r'high\s+conviction\s+long',
            r'strong\s+breakout',
            r'momentum\s+play'
        ]
        
        self.risk_keywords = {
            'high': ['aggressive', 'risky', 'speculative', 'volatile'],
            'medium': ['moderate', 'balanced', 'typical'],
            'low': ['conservative', 'safe', 'secure', 'confirmed']
        }
    
    def analyze_setup_aggressiveness(self, content: str) -> SetupAggressiveness:
        """
        Analyze message content to determine setup aggressiveness.
        
        Args:
            content: Message content to analyze
            
        Returns:
            SetupAggressiveness: Determined aggressiveness level
        """
        content_lower = content.lower()
        
        # Check for conservative indicators
        if any(re.search(pattern, content_lower) for pattern in self.conservative_short_patterns):
            return SetupAggressiveness.CONSERVATIVE
        
        if any(keyword in content_lower for keyword in self.risk_keywords['low']):
            return SetupAggressiveness.CONSERVATIVE
        
        # Check for aggressive indicators
        if any(re.search(pattern, content_lower) for pattern in self.aggressive_long_patterns):
            return SetupAggressiveness.AGGRESSIVE
        
        if any(keyword in content_lower for keyword in self.risk_keywords['high']):
            return SetupAggressiveness.AGGRESSIVE
        
        # Default to moderate
        return SetupAggressiveness.MODERATE
    
    def detect_conservative_short_setup(self, content: str) -> Dict[str, Any]:
        """
        Detect conservative short setup patterns in content.
        
        Args:
            content: Message content to analyze
            
        Returns:
            Dict[str, Any]: Detection results with confidence and details
        """
        result = {
            'detected': False,
            'confidence': 0.0,
            'patterns_matched': [],
            'risk_level': 'unknown'
        }
        
        content_lower = content.lower()
        
        # Check for conservative short patterns
        for pattern in self.conservative_short_patterns:
            if re.search(pattern, content_lower):
                result['patterns_matched'].append(pattern)
                result['confidence'] += 0.25
        
        # Check for additional conservative indicators
        conservative_indicators = [
            'confirmed breakdown', 'support broken', 'volume confirmed',
            'technical breakdown', 'chart pattern', 'resistance turned support'
        ]
        
        for indicator in conservative_indicators:
            if indicator in content_lower:
                result['confidence'] += 0.1
        
        # Determine if detected
        if result['confidence'] >= 0.3:
            result['detected'] = True
            result['risk_level'] = 'low'
        
        result['confidence'] = min(result['confidence'], 1.0)
        return result
    
    def detect_aggressive_long_setup(self, content: str) -> Dict[str, Any]:
        """
        Detect aggressive long setup patterns in content.
        
        Args:
            content: Message content to analyze
            
        Returns:
            Dict[str, Any]: Detection results with confidence and details
        """
        result = {
            'detected': False,
            'confidence': 0.0,
            'patterns_matched': [],
            'risk_level': 'unknown'
        }
        
        content_lower = content.lower()
        
        # Check for aggressive long patterns
        for pattern in self.aggressive_long_patterns:
            if re.search(pattern, content_lower):
                result['patterns_matched'].append(pattern)
                result['confidence'] += 0.25
        
        # Check for additional aggressive indicators
        aggressive_indicators = [
            'strong momentum', 'high volume', 'breakout confirmed',
            'gap up', 'earnings play', 'catalyst driven'
        ]
        
        for indicator in aggressive_indicators:
            if indicator in content_lower:
                result['confidence'] += 0.1
        
        # Determine if detected
        if result['confidence'] >= 0.3:
            result['detected'] = True
            result['risk_level'] = 'high'
        
        result['confidence'] = min(result['confidence'], 1.0)
        return result
    
    def extract_risk_parameters(self, content: str) -> Dict[str, Any]:
        """
        Extract risk-related parameters from message content.
        
        Args:
            content: Message content to analyze
            
        Returns:
            Dict[str, Any]: Risk parameters including stop loss, position size hints
        """
        risk_params = {
            'stop_loss': None,
            'position_size_hint': None,
            'risk_reward_ratio': None,
            'time_horizon': None
        }
        
        # Extract stop loss levels
        stop_patterns = [
            r'stop\s+(?:loss\s+)?(?:at\s+)?\$?(\d+(?:\.\d{2})?)',
            r'sl\s+\$?(\d+(?:\.\d{2})?)',
            r'cut\s+(?:losses\s+)?(?:at\s+)?\$?(\d+(?:\.\d{2})?)'
        ]
        
        for pattern in stop_patterns:
            match = re.search(pattern, content.lower())
            if match:
                try:
                    risk_params['stop_loss'] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Extract position size hints
        size_patterns = [
            r'(?:small|light)\s+position',
            r'(?:large|heavy)\s+position',
            r'(?:full|max)\s+position'
        ]
        
        for pattern in size_patterns:
            if re.search(pattern, content.lower()):
                if 'small' in pattern or 'light' in pattern:
                    risk_params['position_size_hint'] = 'small'
                elif 'large' in pattern or 'heavy' in pattern:
                    risk_params['position_size_hint'] = 'large'
                elif 'full' in pattern or 'max' in pattern:
                    risk_params['position_size_hint'] = 'maximum'
                break
        
        return risk_params
    
    def validate_aplus_criteria(self, setup_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate if a setup meets A+ trading criteria.
        
        Args:
            setup_data: Setup data dictionary to validate
            
        Returns:
            Tuple[bool, List[str]]: (meets_criteria, list_of_issues)
        """
        issues = []
        
        # Check for required elements
        if not setup_data.get('ticker'):
            issues.append("Missing ticker symbol")
        
        if not setup_data.get('setup_type'):
            issues.append("Setup type not identified")
        
        if not setup_data.get('direction'):
            issues.append("Trading direction unclear")
        
        # Check for risk management
        if not setup_data.get('stop_loss') and setup_data.get('aggressiveness') == 'aggressive':
            issues.append("Aggressive setup missing stop loss")
        
        # Validate confidence level
        confidence = setup_data.get('confidence', 0)
        if confidence < 0.3:
            issues.append("Setup confidence too low")
        
        meets_criteria = len(issues) == 0
        return meets_criteria, issues


def analyze_message_with_aplus_rules(content: str) -> Dict[str, Any]:
    """
    Convenience function to analyze message content with A+ rules.
    
    Args:
        content: Message content to analyze
        
    Returns:
        Dict[str, Any]: Complete A+ analysis results
    """
    engine = APlusRulesEngine()
    
    analysis = {
        'aggressiveness': engine.analyze_setup_aggressiveness(content),
        'conservative_short': engine.detect_conservative_short_setup(content),
        'aggressive_long': engine.detect_aggressive_long_setup(content),
        'risk_parameters': engine.extract_risk_parameters(content)
    }
    
    return analysis


def normalize_text_with_emojis(text: str) -> str:
    """
    Normalize text by replacing emojis with standard text markers.
    Extracted from legacy setups parser.
    
    Args:
        text: Raw text with potential emojis
        
    Returns:
        Normalized text with emojis replaced by standard markers
    """
    normalized = text
    for emoji, replacement in EMOJI_MAP.items():
        normalized = normalized.replace(emoji, replacement)
    return normalized


def detect_signal_aggressiveness(line: str) -> str:
    """
    Detect aggressiveness level from signal context.
    Enhanced from legacy setups parser logic.
    
    Args:
        line: Text line containing the signal
        
    Returns:
        Aggressiveness level string
    """
    line_lower = line.lower()
    
    if any(word in line_lower for word in ['aggressive', 'aggressively', 'quick', 'fast']):
        return 'aggressive'
    elif any(word in line_lower for word in ['conservative', 'conservatively', 'careful', 'cautious']):
        return 'conservative'
    elif any(word in line_lower for word in ['high conviction', 'strong', 'confident']):
        return 'high'
    elif any(word in line_lower for word in ['light', 'small', 'minimal']):
        return 'low'
    else:
        return 'medium'


def validate_price_levels(prices: List[float]) -> List[float]:
    """
    Validate price levels are reasonable.
    Extracted from legacy setups parser.
    
    Args:
        prices: List of price levels to validate
        
    Returns:
        List of valid price levels
    """
    if not prices:
        return []
    
    # Filter out obviously wrong prices (e.g. negative or too high)
    return [p for p in prices if 0 < p < 100000]


def extract_signals_from_text(ticker: str, text: str) -> List[Dict[str, Any]]:
    """
    Extract trading signals from text using enhanced patterns.
    Migrated from legacy setups parser with improvements.
    
    Args:
        ticker: The ticker symbol
        text: The text section for this ticker
        
    Returns:
        List of signal dictionaries
    """
    signals = []
    
    # Normalize text first
    normalized_text = normalize_text_with_emojis(text)
    
    # Process each signal category
    for category, patterns in SIGNAL_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, normalized_text, re.IGNORECASE)
            for match in matches:
                try:
                    # Get the full line containing the match
                    line_start = normalized_text.rfind('\n', 0, match.start()) + 1
                    line_end = normalized_text.find('\n', match.end())
                    if line_end == -1:
                        line_end = len(normalized_text)
                    line = normalized_text[line_start:line_end]
                    
                    # Convert the price level to float
                    price_level = float(match.group(1))
                    
                    # Detect aggressiveness from line context
                    aggressiveness = detect_signal_aggressiveness(line)
                    
                    # Determine comparison type and category
                    if category == "breakout":
                        comparison = "above"
                    elif category == "breakdown":
                        comparison = "below"
                    elif category == "rejection":
                        comparison = "near"
                    elif category == "bounce":
                        comparison = "above"
                    else:
                        comparison = "unknown"
                    
                    # Create the signal object
                    signal = {
                        'category': category,
                        'comparison': comparison,
                        'trigger': price_level,
                        'aggressiveness': aggressiveness,
                        'line_context': line.strip()
                    }
                    
                    signals.append(signal)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error extracting signal for {ticker}: {e}")
    
    return signals


def extract_bias_from_text(ticker: str, text: str) -> Optional[Dict[str, Any]]:
    """
    Extract market bias from text using enhanced patterns.
    Migrated from legacy setups parser.
    
    Args:
        ticker: The ticker symbol
        text: The text section for this ticker
        
    Returns:
        Bias dictionary if found, None otherwise
    """
    # Extract bias from text
    for pattern in BIAS_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Format might be (direction, price) or (price, direction) depending on regex
                if len(match) == 2:
                    if match[0].lower() in ["bullish", "bearish"]:
                        direction_str, price_str = match
                    else:
                        price_str, direction_str = match
                
                    # Parse direction
                    direction = direction_str.lower()
                    
                    # Parse price
                    price = float(price_str)
                    
                    # Determine condition type based on context
                    condition_text = re.search(r'(above|below|near)\s+\d+(?:\.\d+)?', text, re.IGNORECASE)
                    if condition_text:
                        condition = condition_text.group(1).lower()
                    else:
                        # Default condition based on direction
                        condition = "above" if direction == "bullish" else "below"
                    
                    # Create bias object
                    bias = {
                        'direction': direction,
                        'condition': condition,
                        'price': price
                    }
                    
                    return bias
            except (ValueError, TypeError) as e:
                logger.warning(f"Error extracting bias for {ticker}: {e}")
    
    return None


def extract_targets_from_text(text: str) -> List[float]:
    """
    Extract price targets from text using enhanced patterns.
    Migrated from legacy setups parser.
    
    Args:
        text: Text to extract targets from
        
    Returns:
        List of target prices
    """
    targets = []
    
    for pattern in TARGET_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                target_price = float(match)
                targets.append(target_price)
            except (ValueError, TypeError):
                continue
    
    # Validate and return unique targets
    valid_targets = validate_price_levels(targets)
    return list(set(valid_targets))