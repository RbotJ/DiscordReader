"""
Setup Service Module

This module provides service functions for handling trading setups,
including persistence, retrieval, and business logic.
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union, Set, Tuple

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
from common.models import (
    TradeSetupMessage,
    TickerSetup as DTOTickerSetup,
    Signal as DTOSignal,
    Bias as DTOBias,
    BiasFlip as DTOBiasFlip,
    SignalCategory,
    Aggressiveness,
    ComparisonType,
    BiasDirection
)

# Configure logger
logger = logging.getLogger(__name__)

class SetupService:
    """Service for handling trading setups."""
    
    @staticmethod
    def save_setup(setup_message: TradeSetupMessage) -> Optional[int]:
        """
        Save a parsed setup message to the database.
        
        Args:
            setup_message: The parsed setup message object
            
        Returns:
            Optional[int]: ID of the saved message or None if error
        """
        try:
            # Create database model instance
            db_setup_message = SetupMessage()
            db_setup_message.date = setup_message.date
            db_setup_message.raw_text = setup_message.raw_text
            db_setup_message.source = setup_message.source
            db_setup_message.created_at = setup_message.created_at or datetime.utcnow()
            
            # Add ticker setups
            for setup in setup_message.setups:
                db_ticker_setup = TickerSetup()
                db_ticker_setup.symbol = setup.symbol
                db_ticker_setup.text = setup.text
                
                # Add signals
                for dto_signal in setup.signals:
                    db_signal = Signal()
                    db_signal.category = SignalCategoryEnum(dto_signal.category.value)
                    db_signal.aggressiveness = AggressivenessEnum(dto_signal.aggressiveness.value)
                    db_signal.comparison = ComparisonTypeEnum(dto_signal.comparison.value)
                    
                    # Handle trigger which could be a single value or a range
                    if isinstance(dto_signal.trigger, (int, float)):
                        db_signal.trigger = dto_signal.trigger
                    else:
                        db_signal.trigger = list(dto_signal.trigger)
                    
                    # Handle targets list
                    db_signal.targets = list(dto_signal.targets)
                    
                    db_ticker_setup.signals.append(db_signal)
                
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
                    
                    db_ticker_setup.bias = db_bias
                
                db_setup_message.ticker_setups.append(db_ticker_setup)
            
            # Save to database
            db.session.add(db_setup_message)
            db.session.commit()
            
            # Return ID of the saved message
            message_id = db_setup_message.id
            logger.info(f"Saved setup message with ID {message_id} containing {len(db_setup_message.ticker_setups)} tickers")
            return message_id
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save setup message: {str(e)}")
            return None
    
    @staticmethod
    def get_setup_by_id(setup_id: int) -> Optional[Dict]:
        """
        Get a setup message by ID with all related data.
        
        Args:
            setup_id: The ID of the setup message
            
        Returns:
            Optional[Dict]: Setup message data as dictionary or None if not found
        """
        try:
            # Query the message
            message = db.session.query(SetupMessage).get(setup_id)
            if not message:
                return None
            
            # Convert to dictionary
            result = {
                'id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'raw_text': message.raw_text,
                'source': message.source,
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'ticker_setups': []
            }
            
            # Add ticker setups
            for ticker_setup in message.ticker_setups:
                setup_data = {
                    'id': ticker_setup.id,
                    'symbol': ticker_setup.symbol,
                    'text': ticker_setup.text,
                    'signals': [],
                    'bias': None
                }
                
                # Add signals
                for signal in ticker_setup.signals:
                    signal_data = {
                        'category': signal.category.value,
                        'aggressiveness': signal.aggressiveness.value,
                        'comparison': signal.comparison.value,
                        'trigger': signal.trigger,
                        'targets': signal.targets
                    }
                    setup_data['signals'].append(signal_data)
                
                # Add bias if present
                if ticker_setup.bias:
                    bias_data = {
                        'direction': ticker_setup.bias.direction.value,
                        'condition': ticker_setup.bias.condition.value,
                        'price': ticker_setup.bias.price,
                        'flip': None
                    }
                    
                    # Add bias flip if present
                    if ticker_setup.bias.bias_flip:
                        bias_data['flip'] = {
                            'direction': ticker_setup.bias.bias_flip.direction.value,
                            'price_level': ticker_setup.bias.bias_flip.price_level
                        }
                    
                    setup_data['bias'] = bias_data
                
                result['ticker_setups'].append(setup_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get setup message: {str(e)}")
            return None
    
    @staticmethod
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
            query = db.session.query(SetupMessage).order_by(SetupMessage.created_at.desc())
            
            if symbol:
                # Use join to filter by ticker symbol
                query = query.join(SetupMessage.ticker_setups).filter(TickerSetup.symbol == symbol)
            
            # Execute query with limit
            messages = query.limit(limit).all()
            
            # Convert to list of dictionaries
            result = []
            for message in messages:
                message_data = {
                    'id': message.id,
                    'date': message.date.isoformat() if message.date else None,
                    'source': message.source,
                    'ticker_symbols': [ts.symbol for ts in message.ticker_setups]
                }
                result.append(message_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recent setups: {str(e)}")
            return []
    
    @staticmethod
    def get_setups_by_symbol(symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get setup messages for a specific ticker symbol.
        
        Args:
            symbol: Ticker symbol to filter by
            limit: Maximum number of setups to return
            
        Returns:
            List[Dict]: List of ticker setups for the specified symbol
        """
        try:
            # Query ticker setups by symbol, with join to get the message date for sorting
            ticker_setups = (db.session.query(TickerSetup)
                .filter(TickerSetup.symbol == symbol)
                .join(TickerSetup.message)
                .order_by(SetupMessage.date.desc())
                .limit(limit)
                .all())
            
            # Convert to list of dictionaries
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
            
        except Exception as e:
            logger.error(f"Failed to get setups by symbol {symbol}: {str(e)}")
            return []