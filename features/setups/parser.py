import re
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from common.models import TradeSetupMessage, TickerSetup, Signal, Bias
from common.models import SignalCategory, Aggressiveness, ComparisonType
from common.utils import publish_event

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for setups (would be replaced with DB in production)
_stored_setups: List[TradeSetupMessage] = []

def parse_setup_message(message_text: str) -> Optional[TradeSetupMessage]:
    """Parse an A+ Trading setup message and extract all setups"""
    try:
        logger.debug(f"Parsing setup message: {message_text[:100]}...")
        
        # Extract date from message (assume ISO format YYYY-MM-DD or similar at start)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message_text)
        message_date = date.fromisoformat(date_match.group(1)) if date_match else date.today()
        
        # Extract ticker setups
        ticker_setups = []
        
        # Look for ticker patterns like $AAPL or $SPY
        ticker_blocks = re.split(r'(\$[A-Z]+)', message_text)
        
        current_ticker = None
        current_block = ""
        
        for block in ticker_blocks:
            if block.startswith('$'):
                # If we have a ticker already, process it
                if current_ticker and current_block:
                    setup = _parse_ticker_block(current_ticker, current_block)
                    if setup:
                        ticker_setups.append(setup)
                
                # Reset for new ticker
                current_ticker = block[1:]  # Remove $ prefix
                current_block = ""
            elif current_ticker:
                # Accumulate block for current ticker
                current_block += block
        
        # Don't forget the last ticker
        if current_ticker and current_block:
            setup = _parse_ticker_block(current_ticker, current_block)
            if setup:
                ticker_setups.append(setup)
        
        # Create the full message
        if ticker_setups:
            setup_message = TradeSetupMessage(
                date=message_date,
                raw_text=message_text,
                setups=ticker_setups
            )
            
            # Store in memory
            _stored_setups.append(setup_message)
            
            # Publish event
            publish_event("setups.new", {
                "message_id": len(_stored_setups),
                "ticker_count": len(ticker_setups),
                "tickers": [setup.symbol for setup in ticker_setups]
            })
            
            return setup_message
        
        logger.warning("No valid ticker setups found in message")
        return None
    
    except Exception as e:
        logger.error(f"Error parsing setup message: {str(e)}")
        return None

def _parse_ticker_block(ticker: str, text: str) -> Optional[TickerSetup]:
    """Parse setup information for a specific ticker"""
    try:
        signals = []
        bias = None
        
        # Extract signals
        # Look for patterns like "breakout above 150" or "breakdown below 120-125 range"
        signal_patterns = [
            (SignalCategory.BREAKOUT, r'breakout\s+(aggressively\s+)?(?:above|over)\s+(\d+\.?\d*)', ComparisonType.ABOVE),
            (SignalCategory.BREAKDOWN, r'breakdown\s+(aggressively\s+)?(?:below|under)\s+(\d+\.?\d*)', ComparisonType.BELOW),
            (SignalCategory.REJECTION, r'reject(?:ion|ing|s)?\s+(at|near|around)\s+(\d+\.?\d*)', ComparisonType.NEAR),
            (SignalCategory.BOUNCE, r'bounce\s+(from|at|near)\s+(\d+\.?\d*)', ComparisonType.NEAR),
        ]
        
        for category, pattern, comparison in signal_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                aggressiveness = Aggressiveness.MEDIUM if match.group(1) and "aggressively" in match.group(1).lower() else Aggressiveness.NONE
                trigger = float(match.group(2))
                
                # Look for targets after this trigger
                target_matches = re.finditer(r'target(?:s)?(?:\s+at)?\s+(\d+\.?\d*)(?:\s+and\s+(\d+\.?\d*))?', text[match.end():], re.IGNORECASE)
                targets = []
                for tmatch in target_matches:
                    targets.append(float(tmatch.group(1)))
                    if tmatch.group(2):
                        targets.append(float(tmatch.group(2)))
                    break  # Just take the first target set for now
                
                if not targets:
                    # Default target is 5% from trigger
                    if category in [SignalCategory.BREAKOUT, SignalCategory.BOUNCE]:
                        targets = [trigger * 1.05]
                    else:
                        targets = [trigger * 0.95]
                
                signal = Signal(
                    category=category,
                    aggressiveness=aggressiveness,
                    comparison=comparison,
                    trigger=trigger,
                    targets=targets
                )
                signals.append(signal)
        
        # Extract bias
        bias_pattern = r'(bullish|bearish)\s+(?:bias\s+)?(above|below|over|under)\s+(\d+\.?\d*)'
        bias_match = re.search(bias_pattern, text, re.IGNORECASE)
        
        if bias_match:
            direction = bias_match.group(1).lower()
            condition_text = bias_match.group(2).lower()
            condition = ComparisonType.ABOVE if condition_text in ["above", "over"] else ComparisonType.BELOW
            price = float(bias_match.group(3))
            
            # Look for bias flip
            flip_pattern = r'flip\s+(bullish|bearish)\s+(?:if|when|on)?\s+(above|below|over|under)\s+(\d+\.?\d*)'
            flip_match = re.search(flip_pattern, text, re.IGNORECASE)
            flip = None
            
            if flip_match:
                flip_direction = flip_match.group(1).lower()
                flip_condition_text = flip_match.group(2).lower()
                flip_condition = ComparisonType.ABOVE if flip_condition_text in ["above", "over"] else ComparisonType.BELOW
                flip_price = float(flip_match.group(3))
                
                flip = {
                    "new_direction": flip_direction,
                    "condition": flip_condition,
                    "price": flip_price
                }
            
            bias = Bias(
                direction=direction,
                condition=condition,
                price=price,
                flip=flip
            )
        
        # Create the ticker setup if we have signals
        if signals:
            return TickerSetup(
                symbol=ticker,
                signals=signals,
                bias=bias
            )
        
        return None
    
    except Exception as e:
        logger.error(f"Error parsing ticker {ticker}: {str(e)}")
        return None

def get_stored_setups() -> List[TradeSetupMessage]:
    """Return all stored setup messages"""
    return _stored_setups

def get_active_setups() -> List[TickerSetup]:
    """Return all active ticker setups (not yet triggered)"""
    active_setups = []
    
    # In a real implementation, we would filter for non-triggered setups
    # For now, return all ticker setups from the last 10 messages
    for message in _stored_setups[-10:]:
        active_setups.extend(message.setups)
    
    return active_setups

def add_manual_setup(ticker_setup: TickerSetup) -> bool:
    """Add a manually created ticker setup"""
    try:
        # Create a new message or add to the last one
        if not _stored_setups:
            message = TradeSetupMessage(
                raw_text=f"Manual setup for {ticker_setup.symbol}",
                setups=[ticker_setup]
            )
            _stored_setups.append(message)
        else:
            _stored_setups[-1].setups.append(ticker_setup)
        
        # Publish event
        publish_event("setups.new", {
            "message_id": len(_stored_setups),
            "ticker_count": 1,
            "tickers": [ticker_setup.symbol],
            "manual": True
        })
        
        return True
    except Exception as e:
        logger.error(f"Error adding manual setup: {str(e)}")
        return False
