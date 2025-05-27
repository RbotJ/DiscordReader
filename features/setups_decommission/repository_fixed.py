"""
Repository for setup persistence and retrieval.

This module provides functionality to save and retrieve trade setups
from the database, maintaining a clean interface between the domain
models and database models.
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Union, Dict, Any

from sqlalchemy.orm.session import Session
from sqlalchemy import desc, func

from app import db
from models import (
    SetupMessage, TickerSetup as DBTickerSetup, Signal as DBSignal,
    Bias as DBBias, BiasFlip as DBBiasFlip,
    SignalCategoryEnum, ComparisonTypeEnum, AggressivenessEnum, BiasDirectionEnum
)
from common.models import (
    TradeSetupMessage, TickerSetup, Signal, Bias, BiasFlip,
    SignalCategory, ComparisonType, Aggressiveness, BiasDirection
)

logger = logging.getLogger(__name__)

class SetupRepository:
    """Repository for trade setup persistence and retrieval."""
    
    @staticmethod
    def save_setup_message(message: TradeSetupMessage) -> int:
        """
        Save a trade setup message to the database.
        
        Args:
            message: The TradeSetupMessage to save
            
        Returns:
            int: The database ID of the saved message
        """
        # Create the database message instance
        db_message = SetupMessage()
        db_message.date = message.date
        db_message.raw_text = message.raw_text
        db_message.source = message.source
        db_message.created_at = message.created_at
        
        # Create empty lists for relationships
        db_message.ticker_setups = []
        
        # Add ticker setups
        for setup in message.setups:
            db_ticker_setup = DBTickerSetup()
            db_ticker_setup.symbol = setup.symbol
            db_ticker_setup.text = setup.text
            
            # Create empty lists for relationships
            db_ticker_setup.signals = []
            
            # Add to parent
            db_message.ticker_setups.append(db_ticker_setup)
            
            # Add signals
            for signal in setup.signals:
                trigger_value = signal.trigger
                # Convert to list for JSON serialization if it's a list
                if isinstance(trigger_value, list):
                    trigger_json = trigger_value
                else:
                    trigger_json = float(trigger_value)
                
                # Create the database signal instance
                db_signal = DBSignal()
                db_signal.category = SignalCategoryEnum[signal.category.name]
                db_signal.aggressiveness = AggressivenessEnum[signal.aggressiveness.name]
                db_signal.comparison = ComparisonTypeEnum[signal.comparison.name]
                db_signal.trigger = trigger_json
                db_signal.targets = [float(t) for t in signal.targets]
                
                # Add to parent
                db_ticker_setup.signals.append(db_signal)
            
            # Add bias if it exists
            if setup.bias:
                bias = setup.bias
                db_bias = DBBias()
                db_bias.direction = BiasDirectionEnum[bias.direction.name]
                db_bias.condition = ComparisonTypeEnum[bias.condition.name]
                db_bias.price = float(bias.price)
                
                # Set parent relationship
                db_ticker_setup.bias = db_bias
                
                # Add bias flip if it exists
                if bias.flip:
                    db_bias_flip = DBBiasFlip()
                    db_bias_flip.direction = BiasDirectionEnum[bias.flip.direction.name]
                    db_bias_flip.price_level = float(bias.flip.price_level)
                    
                    # Set parent relationship
                    db_bias.bias_flip = db_bias_flip
        
        # Save to database
        try:
            db.session.add(db_message)
            db.session.commit()
            logger.info(f"Saved setup message with {len(message.setups)} ticker setups")
            return db_message.id
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving setup message: {str(e)}")
            raise
    
    @staticmethod
    def get_setup_message(message_id: int) -> Optional[TradeSetupMessage]:
        """
        Retrieve a trade setup message by ID.
        
        Args:
            message_id: The database ID of the message
            
        Returns:
            TradeSetupMessage or None if not found
        """
        db_message = SetupMessage.query.get(message_id)
        if not db_message:
            return None
        
        return SetupRepository._convert_db_message_to_domain(db_message)
    
    @staticmethod
    def get_latest_setups(limit: int = 10) -> List[TradeSetupMessage]:
        """
        Retrieve the most recent trade setup messages.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of TradeSetupMessage objects
        """
        db_messages = SetupMessage.query.order_by(
            desc(SetupMessage.created_at)
        ).limit(limit).all()
        
        return [
            SetupRepository._convert_db_message_to_domain(msg)
            for msg in db_messages
        ]
    
    @staticmethod
    def get_setups_by_symbol(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve trade setups for a specific ticker symbol.
        
        Args:
            symbol: The ticker symbol to look for
            limit: Maximum number of setups to retrieve
            
        Returns:
            List of dictionaries with ticker setup data
        """
        db_setups = DBTickerSetup.query.filter_by(symbol=symbol).order_by(
            desc(DBTickerSetup.id)
        ).limit(limit).all()
        
        result = []
        for db_ticker in db_setups:
            ticker_data = SetupRepository._convert_db_ticker_to_dict(db_ticker)
            result.append(ticker_data)
        
        return result
    
    @staticmethod
    def get_setups_by_date(target_date: date) -> List[TradeSetupMessage]:
        """
        Retrieve trade setup messages for a specific date.
        
        Args:
            target_date: The date to filter by
            
        Returns:
            List of TradeSetupMessage objects
        """
        db_messages = SetupMessage.query.filter_by(date=target_date).all()
        
        return [
            SetupRepository._convert_db_message_to_domain(msg)
            for msg in db_messages
        ]
    
    @staticmethod
    def get_setups_by_signal_type(signal_type: SignalCategory, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve trade setups with a specific signal type.
        
        Args:
            signal_type: The signal category to filter by
            limit: Maximum number of setups to retrieve
            
        Returns:
            List of dictionaries with ticker setup data
        """
        db_enum_value = SignalCategoryEnum[signal_type.name]
        
        # Join the ticker setups with their signals and filter by category
        db_setups = db.session.query(DBTickerSetup).join(
            DBSignal
        ).filter(
            DBSignal.category == db_enum_value
        ).order_by(
            desc(DBTickerSetup.id)
        ).limit(limit).all()
        
        result = []
        for db_ticker in db_setups:
            ticker_data = SetupRepository._convert_db_ticker_to_dict(db_ticker)
            result.append(ticker_data)
        
        return result
    
    @staticmethod
    def _convert_db_message_to_domain(db_message: SetupMessage) -> TradeSetupMessage:
        """Convert a database message model to a domain message model."""
        setups = []
        for db_ticker in db_message.ticker_setups:
            # Convert signals
            signals = []
            for db_signal in db_ticker.signals:
                trigger_value = db_signal.trigger
                # Handle range values stored as arrays
                if isinstance(trigger_value, list):
                    trigger = trigger_value
                else:
                    trigger = float(trigger_value)
                    
                signal = Signal(
                    category=SignalCategory[db_signal.category.name],
                    aggressiveness=Aggressiveness[db_signal.aggressiveness.name],
                    comparison=ComparisonType[db_signal.comparison.name],
                    trigger=trigger,
                    targets=[float(t) for t in db_signal.targets]
                )
                signals.append(signal)
            
            # Convert bias if present
            bias = None
            if db_ticker.bias:
                db_bias = db_ticker.bias
                
                # Convert bias flip if present
                bias_flip = None
                if hasattr(db_bias, 'bias_flip') and db_bias.bias_flip:
                    db_flip = db_bias.bias_flip
                    bias_flip = BiasFlip(
                        direction=BiasDirection[db_flip.direction.name],
                        price_level=float(db_flip.price_level)
                    )
                
                bias = Bias(
                    direction=BiasDirection[db_bias.direction.name],
                    condition=ComparisonType[db_bias.condition.name],
                    price=float(db_bias.price),
                    flip=bias_flip
                )
            
            ticker_setup = TickerSetup(
                symbol=db_ticker.symbol,
                signals=signals,
                bias=bias,
                text=db_ticker.text or ""
            )
            setups.append(ticker_setup)
        
        return TradeSetupMessage(
            date=db_message.date,
            raw_text=db_message.raw_text,
            setups=setups,
            source=db_message.source,
            created_at=db_message.created_at
        )
    
    @staticmethod
    def _convert_db_ticker_to_dict(db_ticker: DBTickerSetup) -> Dict[str, Any]:
        """Convert a database ticker setup model to a dictionary."""
        # Convert signals
        signals = []
        for db_signal in db_ticker.signals:
            trigger_value = db_signal.trigger
            # Handle range values stored as arrays
            if isinstance(trigger_value, list):
                trigger = trigger_value
            else:
                trigger = float(trigger_value)
                
            signal_data = {
                "category": db_signal.category.name,
                "aggressiveness": db_signal.aggressiveness.name,
                "comparison": db_signal.comparison.name,
                "trigger": trigger,
                "targets": [float(t) for t in db_signal.targets]
            }
            signals.append(signal_data)
        
        # Convert bias if present
        bias = None
        if db_ticker.bias:
            db_bias = db_ticker.bias
            
            # Convert bias flip if present
            bias_flip = None
            if hasattr(db_bias, 'bias_flip') and db_bias.bias_flip:
                db_flip = db_bias.bias_flip
                bias_flip = {
                    "direction": db_flip.direction.name,
                    "price_level": float(db_flip.price_level)
                }
            
            bias = {
                "direction": db_bias.direction.name,
                "condition": db_bias.condition.name,
                "price": float(db_bias.price),
                "flip": bias_flip
            }
        
        return {
            "id": db_ticker.id,
            "symbol": db_ticker.symbol,
            "message_id": db_ticker.message_id,
            "signals": signals,
            "bias": bias,
            "text": db_ticker.text or ""
        }