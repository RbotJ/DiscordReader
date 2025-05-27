"""
Parsing Rules Module

Contains A+ trading logic and rules for parsing Discord messages.
This module implements specific business rules for identifying conservative shorts,
aggressive longs, and other A+ trading patterns from message content.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
import re
from enum import Enum

logger = logging.getLogger(__name__)


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