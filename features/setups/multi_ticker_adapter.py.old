"""
Multi-Ticker Setup Adapter

This module provides functionality for creating, retrieving, and converting
trade setup data with support for multiple ticker symbols per message.
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from app import db
from common.db_models import (
    SetupModel, TickerSetupModel, SignalModel, BiasModel
)
from features.setups.parser import parse_setup_message

logger = logging.getLogger(__name__)

class MultiTickerAdapter:
    """Adapter for handling multi-ticker setup messages."""
    
    @staticmethod
    def save_setup_message(message_text: str, source: str = "webhook") -> Dict[str, Any]:
        """
        Parse and save a multi-ticker setup message.
        
        Args:
            message_text: The raw text of the setup message
            source: The source of the message (default: webhook)
            
        Returns:
            Dict with setup info including message_id and ticker count
        """
        try:
            # Parse the message
            setup_message = parse_setup_message(message_text, source)
            
            # Create the database model
            db_message = SetupModel(
                date=setup_message.date,
                raw_text=setup_message.raw_text,
                source=setup_message.source,
                created_at=setup_message.created_at
            )
            
            db.session.add(db_message)
            db.session.flush()  # Get the ID without committing
            
            # Process each ticker setup
            for ticker_setup in setup_message.setups:
                # Create ticker setup model
                db_ticker = TickerSetupModel(
                    setup_id=db_message.id,
                    symbol=ticker_setup.symbol,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(db_ticker)
                db.session.flush()  # Get the ID without committing
                
                # Process signals
                for signal in ticker_setup.signals:
                    # Handle different trigger formats
                    trigger_value = signal.trigger
                    if not isinstance(trigger_value, list):
                        trigger_value = float(trigger_value)
                    
                    # Create signal model
                    db_signal = SignalModel(
                        ticker_setup_id=db_ticker.id,
                        category=signal.category.value,
                        aggressiveness=signal.aggressiveness.value,
                        comparison=signal.comparison.value,
                        trigger_value=trigger_value,
                        targets=[float(t) for t in signal.targets],
                        active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(db_signal)
                
                # Process bias if present
                if ticker_setup.bias:
                    bias = ticker_setup.bias
                    
                    # Create bias model
                    db_bias = BiasModel(
                        ticker_setup_id=db_ticker.id,
                        direction=bias.direction.value,
                        condition=bias.condition.value,
                        price=float(bias.price),
                        created_at=datetime.utcnow()
                    )
                    
                    # Add flip if present
                    if bias.flip:
                        db_bias.flip_direction = bias.flip.direction.value
                        db_bias.flip_price_level = float(bias.flip.price_level)
                    
                    db.session.add(db_bias)
            
            # Commit all changes
            db.session.commit()
            
            # Return setup info
            return {
                'message_id': db_message.id,
                'date': db_message.date.isoformat(),
                'ticker_count': len(setup_message.setups),
                'tickers': [setup.symbol for setup in setup_message.setups]
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving multi-ticker setup: {str(e)}")
            raise
    
    @staticmethod
    def get_setups_for_symbol(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent setups for a specific ticker symbol.
        
        Args:
            symbol: The ticker symbol to filter by
            limit: Maximum number of setups to retrieve
            
        Returns:
            List of setup dictionaries
        """
        try:
            # Get ticker setups for symbol
            ticker_setups = TickerSetupModel.query.filter_by(
                symbol=symbol.upper()
            ).order_by(
                TickerSetupModel.created_at.desc()
            ).limit(limit).all()
            
            # Convert to dictionary format
            result = []
            for ticker in ticker_setups:
                # Get parent setup
                setup = SetupModel.query.get(ticker.setup_id)
                
                # Format signals
                signals = []
                for signal in ticker.signals:
                    signal_data = {
                        'id': signal.id,
                        'category': signal.category,
                        'aggressiveness': signal.aggressiveness,
                        'comparison': signal.comparison,
                        'trigger': signal.trigger_value,
                        'targets': signal.targets,
                        'active': signal.active
                    }
                    signals.append(signal_data)
                
                # Format bias if present
                bias = None
                if ticker.bias:
                    bias_data = {
                        'direction': ticker.bias.direction,
                        'condition': ticker.bias.condition,
                        'price': ticker.bias.price
                    }
                    
                    # Add flip if present
                    if ticker.bias.flip_direction and ticker.bias.flip_price_level:
                        bias_data['flip'] = {
                            'direction': ticker.bias.flip_direction,
                            'price_level': ticker.bias.flip_price_level
                        }
                    
                    bias = bias_data
                
                # Create setup dictionary
                setup_data = {
                    'id': ticker.id,
                    'symbol': ticker.symbol,
                    'date': setup.date.isoformat(),
                    'setup_id': setup.id,
                    'signals': signals,
                    'bias': bias,
                    'message': setup.raw_text
                }
                
                result.append(setup_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving setups for {symbol}: {str(e)}")
            raise
    
    @staticmethod
    def get_recent_setups(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent setup messages.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of setup message dictionaries
        """
        try:
            # Get recent setup messages
            setups = SetupModel.query.order_by(
                SetupModel.created_at.desc()
            ).limit(limit).all()
            
            # Convert to dictionary format
            result = []
            for setup in setups:
                # Get ticker symbols
                tickers = [ticker.symbol for ticker in setup.ticker_setups]
                
                # Create setup dictionary
                setup_data = {
                    'id': setup.id,
                    'date': setup.date.isoformat(),
                    'source': setup.source,
                    'created_at': setup.created_at.isoformat(),
                    'ticker_count': len(tickers),
                    'tickers': tickers
                }
                
                result.append(setup_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving recent setups: {str(e)}")
            raise
    
    @staticmethod
    def parse_setup_text(message_text: str, source: str = "test") -> Dict[str, Any]:
        """
        Parse a setup message text without saving to database.
        
        Args:
            message_text: The raw text of the setup message
            source: The source of the message (default: test)
            
        Returns:
            Dictionary with parsed setup data
        """
        try:
            # Parse the message
            setup_message = parse_setup_message(message_text, source)
            
            # Prepare ticker details
            ticker_details = []
            for setup in setup_message.setups:
                # Format signals
                signals = []
                for signal in setup.signals:
                    signal_data = {
                        'category': signal.category.value,
                        'aggressiveness': signal.aggressiveness.value,
                        'comparison': signal.comparison.value,
                        'trigger': signal.trigger,
                        'targets': [float(t) for t in signal.targets]
                    }
                    signals.append(signal_data)
                
                # Format bias if present
                bias = None
                if setup.bias:
                    bias_data = {
                        'direction': setup.bias.direction.value,
                        'condition': setup.bias.condition.value,
                        'price': float(setup.bias.price)
                    }
                    
                    # Add flip if present
                    if setup.bias.flip:
                        bias_data['flip'] = {
                            'direction': setup.bias.flip.direction.value,
                            'price_level': float(setup.bias.flip.price_level)
                        }
                    
                    bias = bias_data
                
                # Create ticker detail dictionary
                ticker_detail = {
                    'symbol': setup.symbol,
                    'signals': signals,
                    'bias': bias
                }
                
                ticker_details.append(ticker_detail)
            
            # Create result dictionary
            result = {
                'date': setup_message.date.isoformat() if setup_message.date else None,
                'tickers': [setup.symbol for setup in setup_message.setups],
                'ticker_count': len(setup_message.setups),
                'ticker_details': ticker_details
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing setup message: {str(e)}")
            raise