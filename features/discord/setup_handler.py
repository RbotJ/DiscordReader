"""
Discord Setup Handler Module

This module handles processing of trade setup messages from Discord,
parsing them into structured data, and storing them in the database.
"""
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union

from features.discord.client import register_setup_callback, send_status_update, send_error_notification
from features.setups.parser import parse_setup_message
from app import db
from common.models import TradeSetupMessage
from common.db_models import SetupModel, TickerSetupModel, SignalModel, BiasModel
from common.event_constants import EventType
from common.redis_utils import publish_event

logger = logging.getLogger(__name__)

def extract_setup_date(message_content: str, message_timestamp: datetime) -> date:
    """
    Extract the setup date from a message or fall back to the message date.
    
    Args:
        message_content: The message content
        message_timestamp: The message timestamp
    
    Returns:
        date: The extracted date
    """
    # Try to extract date from message format: "A+ Trade Setups (Wed, May 14)"
    date_pattern = r"A\+ Trade Setups \(([A-Za-z]+),\s+([A-Za-z]+)\s+(\d{1,2})\)"
    match = re.search(date_pattern, message_content)
    
    if match:
        try:
            # Extract day, month, and day of month
            day_name = match.group(1)
            month_name = match.group(2)
            day_of_month = int(match.group(3))
            
            # Get the current year from the message timestamp
            current_year = message_timestamp.year
            
            # Parse the date
            date_str = f"{day_of_month} {month_name} {current_year}"
            setup_date = datetime.strptime(date_str, "%d %b %Y").date()
            
            # If the extracted date is more than 30 days in the future,
            # it's likely from the previous year (e.g., for messages in January
            # referring to December setups)
            today = datetime.now().date()
            if (setup_date - today).days > 30:
                setup_date = datetime.strptime(f"{day_of_month} {month_name} {current_year-1}", 
                                             "%d %b %Y").date()
            
            # Verify the date is reasonable (not in the future)
            if setup_date > today:
                logger.warning(f"Extracted date {setup_date} is in the future, using message date instead")
                return message_timestamp.date()
                
            return setup_date
        except Exception as e:
            logger.error(f"Error parsing setup date: {e}")
            return message_timestamp.date()
    
    # If no date found, use the message timestamp
    return message_timestamp.date()

def is_relevant_for_today(setup_date: date) -> bool:
    """
    Check if the setup date is relevant for today's market.
    
    Args:
        setup_date: The date of the setup
        
    Returns:
        bool: True if the setup is relevant for today's market
    """
    today = datetime.now().date()
    
    # If setup is from today, it's relevant
    if setup_date == today:
        return True
        
    # If setup is from yesterday and today is a market day, it's relevant
    if (today - setup_date).days == 1:
        # Check if today is a weekday (simple check, ignoring holidays)
        if today.weekday() < 5:  # 0-4 are Monday to Friday
            return True
    
    # If setup is from Friday and today is Monday, it's relevant
    if setup_date.weekday() == 4 and today.weekday() == 0 and (today - setup_date).days <= 3:
        return True
        
    return False

def extract_price_levels(ticker_text: str) -> Dict[str, Union[float, List[float]]]:
    """
    Extract price levels from ticker setup text.
    
    Args:
        ticker_text: Text describing the ticker setup
        
    Returns:
        Dict: Dictionary of price levels
    """
    levels = {}
    
    # Extract support/resistance
    support_match = re.search(r"Support:\s*(\d+\.?\d*)", ticker_text, re.IGNORECASE)
    if support_match:
        levels['support'] = float(support_match.group(1))
        
    resistance_match = re.search(r"Resistance:\s*(\d+\.?\d*)", ticker_text, re.IGNORECASE)
    if resistance_match:
        levels['resistance'] = float(resistance_match.group(1))
    
    # Extract targets
    target_matches = re.finditer(r"Target(?:\s*\d*)?:\s*(\d+\.?\d*)", ticker_text, re.IGNORECASE)
    targets = [float(match.group(1)) for match in target_matches]
    if targets:
        levels['targets'] = targets
        
    # Extract numbered targets
    target1_match = re.search(r"Target\s*1:\s*(\d+\.?\d*)", ticker_text, re.IGNORECASE)
    target2_match = re.search(r"Target\s*2:\s*(\d+\.?\d*)", ticker_text, re.IGNORECASE)
    
    if target1_match or target2_match:
        numbered_targets = []
        if target1_match:
            numbered_targets.append(float(target1_match.group(1)))
        if target2_match:
            numbered_targets.append(float(target2_match.group(1)))
        
        # Only add if we don't already have targets
        if 'targets' not in levels:
            levels['targets'] = numbered_targets
    
    return levels

def extract_bias(ticker_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract market bias from ticker setup text.
    
    Args:
        ticker_text: Text describing the ticker setup
        
    Returns:
        Optional[Dict]: Dictionary with bias information or None
    """
    # Look for bias statements
    bias_pattern = r"(Bullish|Bearish)\s+bias\s+(above|below|near)\s+(\d+\.?\d*)"
    bias_match = re.search(bias_pattern, ticker_text, re.IGNORECASE)
    
    if not bias_match:
        return None
        
    bias = {
        'direction': bias_match.group(1).lower(),
        'condition': bias_match.group(2).lower(),
        'price': float(bias_match.group(3)),
        'flip_direction': None,
        'flip_price_level': None
    }
    
    # Look for flip statements
    flip_pattern = r"flips\s+(bullish|bearish)\s+(above|below|near)\s+(\d+\.?\d*)"
    flip_match = re.search(flip_pattern, ticker_text, re.IGNORECASE)
    
    if flip_match:
        bias['flip_direction'] = flip_match.group(1).lower()
        # For simplicity, we'll ignore the condition and just use the price
        bias['flip_price_level'] = float(flip_match.group(3))
    
    return bias

def extract_signal_type(ticker_line: str) -> Optional[Dict[str, Any]]:
    """
    Extract signal type from ticker line.
    
    Args:
        ticker_line: First line of the ticker setup
        
    Returns:
        Optional[Dict]: Dictionary with signal type information or None
    """
    # Match patterns like: "SPY: Rejection Near 588.8"
    signal_pattern = r"([A-Z]+):\s+(Breakout|Breakdown|Rejection|Bounce)\s+(Above|Below|Near|Between)\s+(\d+\.?\d*)"
    signal_match = re.search(signal_pattern, ticker_line, re.IGNORECASE)
    
    if not signal_match:
        return None
        
    symbol = signal_match.group(1).upper()
    category = signal_match.group(2).lower()
    comparison = signal_match.group(3).lower()
    trigger_value = float(signal_match.group(4))
    
    # Determine aggressiveness (if mentioned)
    aggressiveness = 'none'
    if 'aggressive' in ticker_line.lower():
        aggressiveness = 'high'
    
    return {
        'symbol': symbol,
        'category': category,
        'comparison': comparison,
        'trigger_value': trigger_value,
        'aggressiveness': aggressiveness
    }

def extract_signals(ticker_text: str, ticker_symbol: str) -> List[Dict[str, Any]]:
    """
    Extract trading signals from ticker setup text.
    
    Args:
        ticker_text: Text describing the ticker setup
        ticker_symbol: Symbol of the ticker
        
    Returns:
        List[Dict]: List of signal dictionaries
    """
    signals = []
    
    # Get the first line to extract signal type
    lines = ticker_text.strip().split('\n')
    if not lines:
        return signals
        
    first_line = lines[0]
    signal_info = extract_signal_type(first_line)
    
    if not signal_info:
        return signals
    
    # Extract price levels
    levels = extract_price_levels(ticker_text)
    
    # Create signal
    signal = {
        'symbol': ticker_symbol,
        'category': signal_info['category'],
        'comparison': signal_info['comparison'],
        'trigger_value': signal_info['trigger_value'],
        'aggressiveness': signal_info['aggressiveness'],
        'targets': levels.get('targets', []),
        'active': True
    }
    
    signals.append(signal)
    return signals

def handle_discord_setup_message(message_content: str, message_timestamp: datetime) -> Optional[SetupModel]:
    """
    Process a setup message from Discord.
    
    Args:
        message_content: The content of the Discord message
        message_timestamp: The timestamp of the message
    
    Returns:
        Optional[SetupModel]: The created database model, or None if processing failed
    """
    logger.info("Processing Discord setup message")
    
    try:
        # Extract setup date from message or use message date
        setup_date = extract_setup_date(message_content, message_timestamp)
        
        # Check if the setup is relevant for today's market
        is_relevant = is_relevant_for_today(setup_date)
        
        if not is_relevant:
            logger.info(f"Setup from {setup_date} is not relevant for today's market")
            send_status_update(f"Skipping setup from {setup_date} as it's not relevant for today's market")
            return None
            
        # Parse the setup message
        setup_message = parse_setup_message(message_content, source="discord")
        
        # Update the date with the extracted date
        setup_message.date = setup_date
        
        # Check if we have any valid setups
        if not setup_message.setups:
            logger.warning("No valid trading setups found in Discord message")
            return None
        
        # Store in database
        with db.session.begin():
            # Check if this message is already processed (by checking raw_text)
            existing_setup = SetupModel.query.filter_by(raw_text=message_content).first()
            if existing_setup:
                logger.info(f"Skipping already processed setup message (ID: {existing_setup.id})")
                return existing_setup
            
            # Create setup model
            setup = SetupModel()
            setup.date = setup_message.date
            setup.raw_text = setup_message.raw_text
            setup.source = setup_message.source
            setup.created_at = datetime.utcnow()
            
            db.session.add(setup)
            db.session.flush()  # Flush to get the ID
            
            # Create ticker setups
            ticker_symbols = []
            created_signals = 0
            created_biases = 0
            
            for ticker_setup in setup_message.setups:
                ticker = TickerSetupModel()
                ticker.setup_id = setup.id
                ticker.symbol = ticker_setup.symbol
                ticker.created_at = datetime.utcnow()
                ticker_symbols.append(ticker_setup.symbol)
                
                db.session.add(ticker)
                db.session.flush()  # Flush to get the ID
                
                # Extract bias
                bias_info = extract_bias(ticker_setup.text)
                if bias_info:
                    bias = BiasModel()
                    bias.ticker_setup_id = ticker.id
                    bias.direction = bias_info['direction']
                    bias.condition = bias_info['condition']
                    bias.price = bias_info['price']
                    bias.flip_direction = bias_info['flip_direction']
                    bias.flip_price_level = bias_info['flip_price_level']
                    bias.created_at = datetime.utcnow()
                    
                    db.session.add(bias)
                    created_biases += 1
                    
                    # Publish bias event
                    try:
                        publish_event(EventType.BIAS_CREATED, {
                            'bias_id': bias.id,
                            'ticker_setup_id': ticker.id,
                            'symbol': ticker.symbol,
                            'direction': bias.direction,
                            'price': bias.price
                        })
                    except Exception as e:
                        logger.error(f"Error publishing bias event: {e}")
                
                # Extract signals
                signals_info = extract_signals(ticker_setup.text, ticker_setup.symbol)
                for signal_info in signals_info:
                    signal = SignalModel()
                    signal.ticker_setup_id = ticker.id
                    signal.category = signal_info['category']
                    signal.aggressiveness = signal_info['aggressiveness']
                    signal.comparison = signal_info['comparison']
                    signal.trigger_value = signal_info['trigger_value']
                    signal.targets = signal_info['targets']
                    signal.active = True
                    signal.created_at = datetime.utcnow()
                    
                    db.session.add(signal)
                    created_signals += 1
                    
                    # Publish signal event
                    try:
                        publish_event(EventType.SIGNAL_CREATED, {
                            'signal_id': signal.id,
                            'ticker_setup_id': ticker.id,
                            'symbol': ticker.symbol,
                            'category': signal.category,
                            'trigger_value': signal.trigger_value
                        })
                    except Exception as e:
                        logger.error(f"Error publishing signal event: {e}")
            
            # Publish setup event
            try:
                publish_event(EventType.SETUP_CREATED, {
                    'setup_id': setup.id,
                    'date': setup.date.isoformat(),
                    'source': setup.source,
                    'ticker_count': len(ticker_symbols)
                })
            except Exception as e:
                logger.error(f"Error publishing setup event: {e}")
            
            # Send status update to Discord
            status_msg = (f"Processed new trading setup for {setup.date.strftime('%Y-%m-%d')} with "
                          f"{len(ticker_symbols)} tickers: {', '.join(ticker_symbols[:5])}"
                          f"{' and more' if len(ticker_symbols) > 5 else ''}")
            
            if created_signals > 0 or created_biases > 0:
                status_msg += f" | Created {created_signals} signals and {created_biases} biases"
                
            send_status_update(status_msg)
            
            logger.info(f"Successfully processed Discord setup message with ID {setup.id}")
            return setup
            
    except Exception as e:
        logger.exception(f"Error processing Discord setup message: {e}")
        send_error_notification("Setup Processing", f"Failed to process setup message: {str(e)}")
        return None

def register_discord_setup_handler():
    """Register the callback for Discord setup messages."""
    register_setup_callback(handle_discord_setup_message)
    logger.info("Registered Discord setup message handler")