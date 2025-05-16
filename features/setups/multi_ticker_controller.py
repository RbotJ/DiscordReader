"""
Multi-Ticker Controller Module

This module provides controller functions for handling multi-ticker setup messages.
"""
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import (
    SetupMessage, 
    TickerSetup, 
    Signal, 
    Bias, 
    BiasFlip,
    SignalCategoryEnum,
    AggressivenessEnum,
    ComparisonTypeEnum,
    BiasDirectionEnum
)
from features.setups.parser import SetupParser
from common.models import (
    TradeSetupMessage,
    SignalCategory,
    Aggressiveness,
    ComparisonType,
    BiasDirection
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize parser
parser = SetupParser()

def process_setup_message(text: str, message_date: Optional[date] = None, source: str = "api") -> Dict[str, Any]:
    """
    Process a setup message from text.
    
    Args:
        text: The raw text of the setup message
        message_date: The date of the message, defaults to today
        source: Source of the message, defaults to 'api'
        
    Returns:
        Dict containing processing result with status and data
    """
    try:
        # Use today's date if not provided
        if not message_date:
            message_date = datetime.now().date()
            
        # Parse the message
        setup_message = parser.parse_message(text, date=message_date, source=source)
        
        if not setup_message or not setup_message.setups:
            return {
                'status': 'error',
                'message': 'Failed to parse any ticker setups from the text',
                'raw_text': text
            }
        
        # Try to save to database
        setup_id = save_to_database(setup_message)
        
        if not setup_id:
            return {
                'status': 'error',
                'message': 'Failed to save the setup message to the database',
                'parsed_ticker_count': len(setup_message.setups),
                'tickers': [setup.symbol for setup in setup_message.setups]
            }
        
        # Return success
        return {
            'status': 'success',
            'message': 'Setup message successfully processed',
            'setup_id': setup_id,
            'parsed_ticker_count': len(setup_message.setups),
            'tickers': [setup.symbol for setup in setup_message.setups]
        }
        
    except Exception as e:
        logger.error(f"Error processing setup message: {str(e)}")
        return {
            'status': 'error',
            'message': f'An error occurred while processing the message: {str(e)}',
            'raw_text': text
        }

def save_to_database(setup_message: TradeSetupMessage) -> Optional[int]:
    """
    Save a parsed setup message to the database.
    
    Args:
        setup_message: The parsed setup message
        
    Returns:
        Optional[int]: ID of the saved message or None if error
    """
    try:
        # Create database entry
        db_message = SetupMessage()
        db_message.date = setup_message.date
        db_message.raw_text = setup_message.raw_text
        db_message.source = setup_message.source
        db_message.created_at = setup_message.created_at or datetime.utcnow()
        
        # Add ticker setups
        for setup in setup_message.setups:
            db_ticker = TickerSetup()
            db_ticker.symbol = setup.symbol
            db_ticker.text = setup.text
            
            # Add signals
            for signal in setup.signals:
                db_signal = Signal()
                db_signal.category = SignalCategoryEnum(signal.category.value)
                db_signal.aggressiveness = AggressivenessEnum(signal.aggressiveness.value)
                db_signal.comparison = ComparisonTypeEnum(signal.comparison.value)
                
                # Handle trigger which could be a single value or a range
                if isinstance(signal.trigger, (int, float)):
                    db_signal.trigger = signal.trigger
                else:
                    db_signal.trigger = list(signal.trigger)
                
                # Handle targets list
                db_signal.targets = list(signal.targets)
                
                db_ticker.signals.append(db_signal)
            
            # Add bias if present
            if setup.bias:
                db_bias = Bias()
                db_bias.direction = BiasDirectionEnum(setup.bias.direction.value)
                db_bias.condition = ComparisonTypeEnum(setup.bias.condition.value)
                db_bias.price = setup.bias.price
                
                # Add bias flip if present
                if setup.bias.flip:
                    db_bias_flip = BiasFlip()
                    db_bias_flip.direction = BiasDirectionEnum(setup.bias.flip.direction.value)
                    db_bias_flip.price_level = setup.bias.flip.price_level
                    
                    db_bias.bias_flip = db_bias_flip
                
                db_ticker.bias = db_bias
            
            db_message.ticker_setups.append(db_ticker)
        
        # Save to database
        db.session.add(db_message)
        db.session.commit()
        
        # Get the ID
        message_id = db_message.id
        
        # Log success
        logger.info(f"Saved setup message with ID {message_id} containing {len(db_message.ticker_setups)} ticker setups")
        
        return message_id
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving to database: {str(e)}")
        return None

def get_recent_setups(limit: int = 10, symbol: Optional[str] = None) -> List[Dict]:
    """
    Get recent setup messages with optional filtering by ticker symbol.
    
    Args:
        limit: Maximum number of setups to return
        symbol: Optional ticker symbol to filter by
        
    Returns:
        List[Dict]: List of setup messages
    """
    try:
        # Build query
        query = SetupMessage.query.order_by(SetupMessage.created_at.desc())
        
        if symbol:
            # Join with ticker setups to filter by symbol
            query = query.join(SetupMessage.ticker_setups).filter(TickerSetup.symbol == symbol)
        
        # Get limited results
        messages = query.limit(limit).all()
        
        # Convert to dictionary
        result = []
        for message in messages:
            message_data = {
                'id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'source': message.source,
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'ticker_count': len(message.ticker_setups),
                'ticker_symbols': [ts.symbol for ts in message.ticker_setups]
            }
            result.append(message_data)
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting recent setups: {str(e)}")
        return []
    
    except Exception as e:
        logger.error(f"Error getting recent setups: {str(e)}")
        return []

def get_setup_details(setup_id: int) -> Optional[Dict]:
    """
    Get detailed information about a setup message.
    
    Args:
        setup_id: ID of the setup message
        
    Returns:
        Optional[Dict]: Setup details or None if not found
    """
    try:
        # Get the setup message
        message = SetupMessage.query.get(setup_id)
        if not message:
            return None
        
        # Convert to dictionary
        result = {
            'id': message.id,
            'date': message.date.isoformat() if message.date else None,
            'source': message.source,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'raw_text': message.raw_text,
            'ticker_setups': []
        }
        
        # Add ticker setups
        for ts in message.ticker_setups:
            setup_data = {
                'id': ts.id,
                'symbol': ts.symbol,
                'text': ts.text,
                'signals': [],
                'bias': None
            }
            
            # Add signals
            for signal in ts.signals:
                signal_data = {
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': signal.targets
                }
                setup_data['signals'].append(signal_data)
            
            # Add bias if present
            if ts.bias:
                bias_data = {
                    'direction': ts.bias.direction.value,
                    'condition': ts.bias.condition.value,
                    'price': ts.bias.price,
                    'flip': None
                }
                
                # Add bias flip if present
                if ts.bias.bias_flip:
                    bias_data['flip'] = {
                        'direction': ts.bias.bias_flip.direction.value,
                        'price_level': ts.bias.bias_flip.price_level
                    }
                
                setup_data['bias'] = bias_data
            
            result['ticker_setups'].append(setup_data)
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting setup details: {str(e)}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting setup details: {str(e)}")
        return None

def get_setups_by_symbol(symbol: str, limit: int = 10) -> List[Dict]:
    """
    Get setups for a specific ticker symbol.
    
    Args:
        symbol: Ticker symbol to filter by
        limit: Maximum number of setups to return
        
    Returns:
        List[Dict]: List of setups for the symbol
    """
    try:
        # Query ticker setups
        ticker_setups = (TickerSetup.query
            .filter(TickerSetup.symbol == symbol)
            .join(TickerSetup.message)
            .order_by(SetupMessage.date.desc())
            .limit(limit)
            .all())
        
        # Convert to dictionary
        result = []
        for ts in ticker_setups:
            setup_data = {
                'id': ts.id,
                'symbol': ts.symbol,
                'message_id': ts.message_id,
                'message_date': ts.message.date.isoformat() if ts.message and ts.message.date else None,
                'text': ts.text,
                'signals': [],
                'bias': None
            }
            
            # Add signals
            for signal in ts.signals:
                signal_data = {
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': signal.targets
                }
                setup_data['signals'].append(signal_data)
            
            # Add bias if present
            if ts.bias:
                bias_data = {
                    'direction': ts.bias.direction.value,
                    'condition': ts.bias.condition.value,
                    'price': ts.bias.price,
                    'flip': None
                }
                
                # Add bias flip if present
                if ts.bias.bias_flip:
                    bias_data['flip'] = {
                        'direction': ts.bias.bias_flip.direction.value,
                        'price_level': ts.bias.bias_flip.price_level
                    }
                
                setup_data['bias'] = bias_data
            
            result.append(setup_data)
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting setups by symbol: {str(e)}")
        return []
    
    except Exception as e:
        logger.error(f"Error getting setups by symbol: {str(e)}")
        return []