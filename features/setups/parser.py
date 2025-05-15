import re
import logging
from typing import List, Optional, Dict, Any, Union
from common.models import TickerSetup, Signal, Bias, SignalCategory, ComparisonType, Aggressiveness, BiasDirection

# Configure logging
logger = logging.getLogger(__name__)

class SetupParser:
    """
    Parser for A+ Trading setup messages.
    Extracts symbols, signals, targets, and biases from raw text.
    """
    
    def __init__(self):
        self.ticker_pattern = r'\$([A-Z]+)'
        self.price_pattern = r'(\$?\d+\.?\d*)'
        self.bias_pattern = r'(bullish|bearish)\s+(above|below)\s+' + self.price_pattern
        self.breakout_pattern = r'breakout\s+(above|over)\s+' + self.price_pattern
        self.breakdown_pattern = r'breakdown\s+(below|under)\s+' + self.price_pattern
        self.rejection_pattern = r'rejection\s+(at|near)\s+' + self.price_pattern
        self.bounce_pattern = r'bounce\s+(from|at|near)\s+' + self.price_pattern
        self.targets_pattern = r'target(?:s)?\s+(?:is|are|:)?\s+(' + self.price_pattern + r'(?:\s*,\s*' + self.price_pattern + r')*)'
        self.aggressiveness_pattern = r'(low|medium|high)\s+aggression'
        self.bias_flip_pattern = r'flip\s+(bullish|bearish)\s+(above|below)\s+' + self.price_pattern
    
    def parse_raw_setup(self, raw_text: str) -> List[TickerSetup]:
        """
        Parse raw setup text and extract ticker setups.
        
        Args:
            raw_text: The raw text from Discord/Email containing setup information
            
        Returns:
            List of parsed TickerSetup objects
        """
        logger.debug(f"Parsing raw setup text: {raw_text[:100]}...")
        
        # Split the text by lines or paragraphs
        sections = [section.strip() for section in re.split(r'\n\s*\n|\r\n\s*\r\n', raw_text) if section.strip()]
        
        ticker_setups = []
        
        for section in sections:
            # Extract ticker symbol
            ticker_match = re.search(self.ticker_pattern, section)
            if not ticker_match:
                logger.debug(f"No ticker found in section: {section[:50]}...")
                continue
                
            symbol = ticker_match.group(1)
            logger.debug(f"Found ticker: {symbol}")
            
            # Extract signals
            signals = []
            
            # Look for breakout signals
            breakout_matches = re.finditer(self.breakout_pattern, section, re.IGNORECASE)
            for match in breakout_matches:
                comparison = ComparisonType.ABOVE if match.group(1).lower() in ("above", "over") else ComparisonType.ABOVE
                trigger = float(match.group(2).replace('$', ''))
                signals.append(Signal(
                    category=SignalCategory.BREAKOUT,
                    comparison=comparison,
                    trigger=trigger,
                    targets=self._extract_targets(section)
                ))
                logger.debug(f"Found breakout signal: {comparison} {trigger}")
            
            # Look for breakdown signals
            breakdown_matches = re.finditer(self.breakdown_pattern, section, re.IGNORECASE)
            for match in breakdown_matches:
                comparison = ComparisonType.BELOW if match.group(1).lower() in ("below", "under") else ComparisonType.BELOW
                trigger = float(match.group(2).replace('$', ''))
                signals.append(Signal(
                    category=SignalCategory.BREAKDOWN,
                    comparison=comparison,
                    trigger=trigger,
                    targets=self._extract_targets(section)
                ))
                logger.debug(f"Found breakdown signal: {comparison} {trigger}")
            
            # Look for rejection signals
            rejection_matches = re.finditer(self.rejection_pattern, section, re.IGNORECASE)
            for match in rejection_matches:
                comparison = ComparisonType.NEAR
                trigger = float(match.group(2).replace('$', ''))
                signals.append(Signal(
                    category=SignalCategory.REJECTION,
                    comparison=comparison,
                    trigger=trigger,
                    targets=self._extract_targets(section)
                ))
                logger.debug(f"Found rejection signal: {comparison} {trigger}")
            
            # Look for bounce signals
            bounce_matches = re.finditer(self.bounce_pattern, section, re.IGNORECASE)
            for match in bounce_matches:
                comparison = ComparisonType.NEAR
                trigger = float(match.group(2).replace('$', ''))
                signals.append(Signal(
                    category=SignalCategory.BOUNCE,
                    comparison=comparison,
                    trigger=trigger,
                    targets=self._extract_targets(section)
                ))
                logger.debug(f"Found bounce signal: {comparison} {trigger}")
            
            # Extract bias if available
            bias = self._extract_bias(section)
            if bias:
                logger.debug(f"Found bias: {bias.direction} {bias.condition} {bias.price}")
            
            # Extract aggressiveness
            aggressiveness = self._extract_aggressiveness(section)
            
            # Apply aggressiveness to all signals
            for signal in signals:
                signal.aggressiveness = aggressiveness
            
            # Create ticker setup if we have at least one signal
            if signals:
                ticker_setup = TickerSetup(
                    symbol=symbol,
                    signals=signals,
                    bias=bias
                )
                ticker_setups.append(ticker_setup)
                logger.info(f"Created setup for {symbol} with {len(signals)} signals")
        
        return ticker_setups
    
    def _extract_targets(self, text: str) -> List[float]:
        """Extract price targets from text."""
        targets = []
        targets_match = re.search(self.targets_pattern, text, re.IGNORECASE)
        
        if targets_match:
            targets_text = targets_match.group(1)
            # Split by commas and convert to floats
            for target in re.findall(self.price_pattern, targets_text):
                try:
                    targets.append(float(target.replace('$', '')))
                except ValueError:
                    pass
        
        return targets
    
    def _extract_bias(self, text: str) -> Optional[Bias]:
        """Extract bias information from text."""
        bias_match = re.search(self.bias_pattern, text, re.IGNORECASE)
        
        if not bias_match:
            return None
        
        direction = BiasDirection.BULLISH if bias_match.group(1).lower() == "bullish" else BiasDirection.BEARISH
        condition = ComparisonType.ABOVE if bias_match.group(2).lower() == "above" else ComparisonType.BELOW
        price = float(bias_match.group(3).replace('$', ''))
        
        # Look for bias flip
        flip = None
        flip_match = re.search(self.bias_flip_pattern, text, re.IGNORECASE)
        
        if flip_match:
            flip_direction = BiasDirection.BULLISH if flip_match.group(1).lower() == "bullish" else BiasDirection.BEARISH
            flip_price = float(flip_match.group(3).replace('$', ''))
            
            from common.models import BiasFlip
            flip = BiasFlip(
                direction=flip_direction,
                price_level=flip_price
            )
        
        return Bias(
            direction=direction,
            condition=condition,
            price=price,
            flip=flip
        )
    
    def _extract_aggressiveness(self, text: str) -> Aggressiveness:
        """Extract aggressiveness level from text."""
        aggression_match = re.search(self.aggressiveness_pattern, text, re.IGNORECASE)
        
        if not aggression_match:
            return Aggressiveness.NONE
        
        aggression_text = aggression_match.group(1).lower()
        
        if aggression_text == "low":
            return Aggressiveness.LOW
        elif aggression_text == "medium":
            return Aggressiveness.MEDIUM
        elif aggression_text == "high":
            return Aggressiveness.HIGH
        
        return Aggressiveness.NONE
