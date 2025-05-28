"""
Parsing Models Module

Database models for parsed trading setups.
Contains the SetupModel for storing structured trading setup information
extracted from Discord messages.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, Date
from sqlalchemy.dialects.postgresql import JSONB
from common.db import db

logger = logging.getLogger(__name__)


# Legacy parsing models have been replaced by new schema
# Use features.models.new_schema.TradeSetup and ParsedLevel instead

from features.models.new_schema import TradeSetup, ParsedLevel

# Re-export for backward compatibility during migration
SetupModel = TradeSetup
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core setup information
    ticker = Column(String(10), nullable=False, index=True)
    setup_type = Column(String(50), nullable=False)
    direction = Column(String(20), nullable=False)  # bullish, bearish, neutral
    
    # Price and targets
    price_target = Column(Float, nullable=True)
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    
    # Setup metadata
    confidence = Column(Float, default=0.5)
    aggressiveness = Column(String(20), default='moderate')  # conservative, moderate, aggressive
    position_size_hint = Column(String(20), nullable=True)  # small, medium, large, maximum
    
    # Temporal information
    date = Column(Date, nullable=False, index=True)
    expiration_date = Column(Date, nullable=True)
    
    # Source and context
    source_message_id = Column(String(64), nullable=False, index=True)
    context = Column(Text, nullable=True)
    
    # Setup status
    active = Column(Boolean, default=True, index=True)
    executed = Column(Boolean, default=False, index=True)
    triggered = Column(Boolean, default=False)
    
    # Additional data
    risk_parameters = Column(JSONB, nullable=True)
    analysis_data = Column(JSONB, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        """Initialize SetupModel with provided arguments."""
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        """String representation of the setup model."""
        return f"<SetupModel {self.ticker} {self.setup_type} {self.direction}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the setup
        """
        return {
            'id': self.id,
            'ticker': self.ticker,
            'setup_type': self.setup_type,
            'direction': self.direction,
            'price_target': self.price_target,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'confidence': self.confidence,
            'aggressiveness': self.aggressiveness,
            'position_size_hint': self.position_size_hint,
            'date': self.date.isoformat() if self.date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'source_message_id': self.source_message_id,
            'context': self.context,
            'active': self.active,
            'executed': self.executed,
            'triggered': self.triggered,
            'risk_parameters': self.risk_parameters,
            'analysis_data': self.analysis_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_parsed_data(
        cls, 
        ticker: str, 
        setup_data: Dict[str, Any], 
        source_message_id: str
    ) -> 'SetupModel':
        """
        Create a SetupModel from parsed data dictionary.
        Pure data structure creation - no database operations.
        
        Args:
            ticker: Stock ticker symbol
            setup_data: Dictionary containing parsed setup information
            source_message_id: Discord message ID that generated this setup
            
        Returns:
            SetupModel: New model instance (not saved to database)
        """
        return cls(
            ticker=ticker.upper(),
            setup_type=setup_data.get('setup_type', 'unknown'),
            direction=setup_data.get('direction', 'neutral'),
            price_target=setup_data.get('price_target'),
            entry_price=setup_data.get('entry_price'),
            stop_loss=setup_data.get('stop_loss'),
            confidence=setup_data.get('confidence', 0.5),
            aggressiveness=setup_data.get('aggressiveness', 'moderate'),
            position_size_hint=setup_data.get('position_size_hint'),
            date=setup_data.get('date', date.today()),
            expiration_date=setup_data.get('expiration_date'),
            source_message_id=source_message_id,
            context=setup_data.get('context', ''),
            risk_parameters=setup_data.get('risk_parameters'),
            analysis_data=setup_data.get('analysis_data')
        )
    
    def mark_as_executed(self, execution_price: Optional[float] = None) -> None:
        """
        Mark this setup as executed.
        Pure data update - no database operations.
        
        Args:
            execution_price: Optional price at which setup was executed
        """
        self.executed = True
        if execution_price:
            self.entry_price = execution_price
        self.updated_at = datetime.utcnow()
    
    def mark_as_triggered(self) -> None:
        """Mark this setup as triggered. Pure data update - no database operations."""
        self.triggered = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate this setup. Pure data update - no database operations."""
        self.active = False
        self.updated_at = datetime.utcnow()
    
    def update_confidence(self, new_confidence: float) -> None:
        """
        Update the confidence score for this setup.
        Pure data update - no database operations.
        
        Args:
            new_confidence: New confidence score (0.0 to 1.0)
        """
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_active_setups(cls, ticker: Optional[str] = None) -> List['SetupModel']:
        """
        Get active setups, optionally filtered by ticker.
        
        Args:
            ticker: Optional ticker to filter by
            
        Returns:
            List[SetupModel]: Active setups
        """
        query = cls.query.filter_by(active=True, executed=False)
        if ticker:
            query = query.filter_by(ticker=ticker.upper())
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_setups_by_message(cls, message_id: str) -> List['SetupModel']:
        """
        Get all setups created from a specific message.
        
        Args:
            message_id: Discord message ID
            
        Returns:
            List[SetupModel]: Setups from the specified message
        """
        return cls.query.filter_by(source_message_id=message_id).all()
    
    @classmethod
    def get_setups_by_date_range(
        cls, 
        start_date: date, 
        end_date: date,
        active_only: bool = True
    ) -> List['SetupModel']:
        """
        Get setups within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            active_only: Whether to return only active setups
            
        Returns:
            List[SetupModel]: Setups within the date range
        """
        query = cls.query.filter(
            cls.date >= start_date,
            cls.date <= end_date
        )
        
        if active_only:
            query = query.filter_by(active=True)
        
        return query.order_by(cls.date.desc(), cls.created_at.desc()).all()
    
    @classmethod
    def get_high_confidence_setups(cls, min_confidence: float = 0.7) -> List['SetupModel']:
        """
        Get setups with confidence above threshold.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            List[SetupModel]: High confidence setups
        """
        return cls.query.filter(
            cls.confidence >= min_confidence,
            cls.active == True,
            cls.executed == False
        ).order_by(cls.confidence.desc()).all()
    
    @classmethod
    def get_setup_statistics(cls) -> Dict[str, Any]:
        """
        Get statistics about stored setups.
        
        Returns:
            Dict[str, Any]: Setup statistics
        """
        total_setups = cls.query.count()
        active_setups = cls.query.filter_by(active=True).count()
        executed_setups = cls.query.filter_by(executed=True).count()
        triggered_setups = cls.query.filter_by(triggered=True).count()
        
        avg_confidence = db.session.query(db.func.avg(cls.confidence)).scalar() or 0.0
        
        return {
            'total_setups': total_setups,
            'active_setups': active_setups,
            'executed_setups': executed_setups,
            'triggered_setups': triggered_setups,
            'average_confidence': round(float(avg_confidence), 3),
            'execution_rate': round((executed_setups / total_setups * 100), 2) if total_setups > 0 else 0.0
        }


# Legacy models from setups/models.py - consolidated here for parsing slice
class SetupMessageModel(db.Model):
    """Legacy setup message model - consolidated into parsing slice."""
    __tablename__ = 'setup_messages'
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), nullable=True)
    source = Column(String(50), nullable=False, default='discord')
    raw_text = Column(Text, nullable=False)
    parsed_data = Column(JSONB, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ticker_setups = db.relationship("TickerSetupModel", back_populates="message", cascade="all, delete-orphan")


class TickerSetupModel(db.Model):
    """Legacy ticker setup model - consolidated into parsing slice."""
    __tablename__ = 'ticker_setups'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    setup_message_id = Column(Integer, db.ForeignKey('setup_messages.id', ondelete='CASCADE'), nullable=True)
    text = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    direction = Column(String(10), nullable=True)
    price_level = Column(Float, nullable=True)
    target1 = Column(Float, nullable=True)
    target2 = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    message = db.relationship("SetupMessageModel", back_populates="ticker_setups")