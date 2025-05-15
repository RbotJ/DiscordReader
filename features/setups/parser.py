"""
Parser module for A+ Trading setups.

This module handles parsing raw setup messages to extract structured data
about trading setups, signals, and biases.
"""
import re
import logging
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Any, Union

# Import models
from common.models import (
    TradeSetupMessage, 
    TickerSetup, 
    Signal, 
    Bias, 
    BiasFlip,
    SignalCategory, 
    ComparisonType, 
    Aggressiveness,
    BiasDirection
)

# Configure logger
logger = logging.getLogger(__name__)

# Emoji mappings
EMOJI_MAP = {
    "🔼": SignalCategory.BREAKOUT,
    "🔻": SignalCategory.BREAKDOWN,
    "❌": SignalCategory.REJECTION,
    "🔄": SignalCategory.BOUNCE,
    "🌀": SignalCategory.BOUNCE,
}

# Regular expressions for parsing
DATE_PATTERN = r"A\+\s+Trade\s+Setups\s+(?:—|-)?\s*(\w+)\s+(\w+)\s+(\d+)"
TICKER_PATTERN = r"^(\d+\)?\s*)?([A-Z]+)(?:\s*$|\s+)"
SIGNAL_PATTERN = r"(🔼|🔻|❌|🔄|🌀)\s*(.*?)(?:$|(?=\s*[🔼🔻❌🔄🌀⚠️]))"
PRICE_PATTERN = r"([\d.]+)"
BIAS_PATTERN = r"⚠️\s*(.*?)(?:$|(?=\s*[🔼🔻❌🔄🌀]))"

# Aggressiveness keywords
AGGRESSIVE_KEYWORDS = ["aggressive", "agg"]
CONSERVATIVE_KEYWORDS = ["conservative", "con"]

def parse_date(text: str) -> Optional[date]:
    """Parse date from the trade setup message header."""
    match = re.search(DATE_PATTERN, text, re.IGNORECASE)
    if not match:
        return None
    
    day_name, month_name, day = match.groups()
    
    # Handle the current year
    today = datetime.now()
    year = today.year
    
    # Create a date string and parse it
    date_str = f"{day} {month_name} {year}"
    try:
        parsed_date = datetime.strptime(date_str, "%d %b %Y").date()
        return parsed_date
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}")
        return None

def extract_tickers(text: str) -> List[Tuple[str, str]]:
    """Extract ticker symbols and their associated text blocks from the message."""
    lines = text.split('\n')
    tickers = []
    current_ticker = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for a new ticker
        ticker_match = re.match(TICKER_PATTERN, line)
        if ticker_match and not line.startswith(("—", "-")):
            # If we already have a ticker, save it
            if current_ticker:
                tickers.append((current_ticker, '\n'.join(current_text)))
                current_text = []
            
            # Extract the new ticker
            current_ticker = ticker_match.group(2)
            current_text.append(line)
        elif current_ticker:
            # Continue with the current ticker
            current_text.append(line)
    
    # Add the last ticker
    if current_ticker and current_text:
        tickers.append((current_ticker, '\n'.join(current_text)))
    
    return tickers

def parse_signal(signal_text: str) -> Optional[Signal]:
    """Parse a signal from text."""
    # Extract emoji and rest of the text
    emoji = signal_text[0] if signal_text else None
    if not emoji or emoji not in EMOJI_MAP:
        return None
    
    category = EMOJI_MAP[emoji]
    remaining_text = signal_text[1:].strip()
    
    # Check for aggressiveness
    aggressiveness = Aggressiveness.NONE
    for aggressive in AGGRESSIVE_KEYWORDS:
        if aggressive.lower() in remaining_text.lower():
            aggressiveness = Aggressiveness.AGGRESSIVE
            break
            
    for conservative in CONSERVATIVE_KEYWORDS:
        if conservative.lower() in remaining_text.lower():
            aggressiveness = Aggressiveness.CONSERVATIVE
            break
    
    # Extract price levels
    price_matches = re.findall(PRICE_PATTERN, remaining_text)
    if not price_matches:
        return None
    
    prices = [float(p) for p in price_matches]
    
    # Determine comparison type and trigger value
    comparison = ComparisonType.NEAR  # Default
    if "above" in remaining_text.lower():
        comparison = ComparisonType.ABOVE
    elif "below" in remaining_text.lower():
        comparison = ComparisonType.BELOW
    elif "from" in remaining_text.lower() or "zone" in remaining_text.lower():
        comparison = ComparisonType.RANGE
        if len(prices) < 2:
            # Not enough prices for a range
            comparison = ComparisonType.NEAR
    
    # Extract trigger and targets
    if comparison == ComparisonType.RANGE and len(prices) >= 2:
        # For bounce zones, the first two prices represent the range
        trigger = [prices[0], prices[1]]
        targets = prices[2:] if len(prices) > 2 else []
    else:
        # For other signals, the first price is the trigger
        trigger = prices[0]
        targets = prices[1:] if len(prices) > 1 else []
    
    # Create the signal object
    return Signal(
        category=category,
        aggressiveness=aggressiveness,
        comparison=comparison,
        trigger=trigger,
        targets=targets
    )

def parse_bias(bias_text: str) -> Optional[Bias]:
    """Parse a bias from text."""
    if not bias_text or not bias_text.strip():
        return None
    
    text = bias_text.lower()
    
    # Determine direction
    direction = BiasDirection.BULLISH if "bullish" in text else BiasDirection.BEARISH
    
    # Extract price level
    price_matches = re.findall(PRICE_PATTERN, bias_text)
    if not price_matches:
        return None
    
    price = float(price_matches[0])
    
    # Determine condition
    condition = ComparisonType.ABOVE
    if "below" in text or "under" in text:
        condition = ComparisonType.BELOW
    
    # Check for bias flip
    flip = None
    if "flip" in text or "flips" in text:
        flip_direction = BiasDirection.BULLISH if "bullish" in text[text.find("flip"):] else BiasDirection.BEARISH
        
        # Find additional price level for flip
        if len(price_matches) > 1:
            flip_price = float(price_matches[1])
            
            flip = BiasFlip(
                direction=flip_direction,
                price_level=flip_price
            )
    
    # Create the bias object
    return Bias(
        direction=direction,
        condition=condition,
        price=price,
        flip=flip
    )

def parse_ticker_setup(ticker: str, text: str) -> TickerSetup:
    """Parse a ticker setup from text."""
    signals = []
    bias = None
    
    # Extract signals
    signal_matches = re.findall(SIGNAL_PATTERN, text, re.DOTALL)
    for emoji, signal_text in signal_matches:
        full_signal_text = emoji + signal_text
        signal = parse_signal(full_signal_text)
        if signal:
            signals.append(signal)
    
    # Extract bias
    bias_match = re.search(BIAS_PATTERN, text, re.DOTALL)
    if bias_match:
        bias_text = bias_match.group(1)
        bias = parse_bias(bias_text)
    
    # Create the ticker setup
    return TickerSetup(
        symbol=ticker,
        signals=signals,
        bias=bias
    )

def parse_setup_message(message: str, source: str = "manual") -> TradeSetupMessage:
    """Parse a full trade setup message."""
    # Parse the date
    setup_date = parse_date(message) or datetime.now().date()
    
    # Extract ticker setups
    ticker_blocks = extract_tickers(message)
    setups = []
    
    for ticker, text in ticker_blocks:
        ticker_setup = parse_ticker_setup(ticker, text)
        setups.append(ticker_setup)
    
    # Create the trade setup message
    return TradeSetupMessage(
        date=setup_date,
        raw_text=message,
        setups=setups,
        source=source
    )

def save_setup_to_db(setup: TradeSetupMessage) -> bool:
    """Save a parsed setup to the database."""
    from common.db_models import SetupModel, TickerSetupModel, SignalModel, BiasModel
    from app import db
    from sqlalchemy.sql import insert
    
    try:
        # Create setup message using core insert
        setup_stmt = insert(SetupModel).values(
            date=setup.date,
            raw_text=setup.raw_text,
            source=setup.source
        ).returning(SetupModel.id)
        
        setup_id = db.session.execute(setup_stmt).scalar_one()
        
        # Create ticker setups
        for ticker_setup in setup.setups:
            # Insert ticker setup
            ticker_stmt = insert(TickerSetupModel).values(
                setup_id=setup_id,
                symbol=ticker_setup.symbol
            ).returning(TickerSetupModel.id)
            
            ticker_id = db.session.execute(ticker_stmt).scalar_one()
            
            # Create signals
            for signal in ticker_setup.signals:
                # Use core insert for signals
                signal_stmt = insert(SignalModel).values(
                    ticker_setup_id=ticker_id,
                    category=signal.category.value,
                    aggressiveness=signal.aggressiveness.value,
                    comparison=signal.comparison.value,
                    trigger_value=signal.trigger if isinstance(signal.trigger, float) else signal.trigger,
                    targets=signal.targets
                )
                db.session.execute(signal_stmt)
            
            # Create bias if it exists
            if ticker_setup.bias:
                flip_direction = None
                flip_price = None
                
                if ticker_setup.bias.flip:
                    flip_direction = ticker_setup.bias.flip.direction.value
                    flip_price = ticker_setup.bias.flip.price_level
                
                # Use core insert for bias
                bias_stmt = insert(BiasModel).values(
                    ticker_setup_id=ticker_id,
                    direction=ticker_setup.bias.direction.value,
                    condition=ticker_setup.bias.condition.value,
                    price=ticker_setup.bias.price,
                    flip_direction=flip_direction,
                    flip_price_level=flip_price
                )
                db.session.execute(bias_stmt)
        
        # Commit the transaction
        db.session.commit()
        return True
    
    except Exception as e:
        logger.error(f"Error saving setup to database: {e}")
        db.session.rollback()
        return False

def process_setup_message(message: str, source: str = "manual") -> Dict[str, Any]:
    """Process a trade setup message and save it to the database."""
    try:
        # Parse the message
        setup = parse_setup_message(message, source)
        
        # Save to database
        success = save_setup_to_db(setup)
        
        if success:
            return {
                "success": True,
                "setup_date": setup.date,
                "tickers": [s.symbol for s in setup.setups],
                "signal_count": sum(len(s.signals) for s in setup.setups)
            }
        else:
            return {
                "success": False,
                "error": "Failed to save setup to database"
            }
    
    except Exception as e:
        logger.error(f"Error processing setup message: {e}")
        return {
            "success": False,
            "error": str(e)
        }