"""
Parsing Models Module

New schema models for the parsing vertical slice.
Contains TradeSetup and ParsedLevel models for storing structured trading setup information
extracted from Discord messages.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from common.db import db

logger = logging.getLogger(__name__)


class TradeSetup(db.Model):
    """
    Refactored schema model for trade setups using the new token-based parsing approach.
    Supports structured setup identification with flexible labeling and audit capabilities.
    """
    __tablename__ = "trade_setups"

    # Use string ID from the refactored parser (e.g., "20250616_NVDA_Setup_1")
    id = Column(String(50), primary_key=True)
    
    # Core setup information
    message_id = Column(String(64), nullable=False, index=True)  # Discord message ID
    ticker = Column(String(10), nullable=False, index=True)
    trading_day = Column(Date, nullable=False, index=True)
    index = Column(Integer, nullable=False)  # 1-based order within ticker section
    
    # Price information (required fields from refactored parser)
    trigger_level = Column(Numeric(10, 4), nullable=False)  # Primary entry price
    target_prices = Column(JSONB, nullable=False)  # Array of target prices
    
    # Direction and classification (required fields)
    direction = Column(String(10), nullable=False)  # 'long' or 'short'
    label = Column(String(50), nullable=True)  # Human-readable label (AggressiveBreakout, etc.)
    keywords = Column(JSONB, nullable=True)  # Array of matched keywords
    emoji_hint = Column(String(10), nullable=True)  # Emoji indicator from message
    
    # Original content
    raw_line = Column(Text, nullable=False)  # Original setup line from message
    
    # Legacy fields for backward compatibility
    setup_type = Column(String(50), nullable=True)  # Derived from label
    profile_name = Column(String(50), nullable=True)  # Same as label
    bias_note = Column(Text, nullable=True)  # Per-ticker bias from message
    
    # Status tracking
    active = Column(Boolean, default=True, index=True)
    confidence_score = Column(Float, nullable=True)
    
    # Metadata
    parsed_metadata = Column(JSONB, nullable=True)  # Additional parsing data
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    levels = relationship("ParsedLevel", back_populates="setup", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<TradeSetup(id={self.id}, ticker={self.ticker}, setup_type={self.setup_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'ticker': self.ticker,
            'trading_day': self.trading_day.isoformat() if self.trading_day is not None else None,
            'index': self.index,
            'trigger_level': float(self.trigger_level) if hasattr(self, '_trigger_level') and self.trigger_level is not None else None,
            'target_prices': self.target_prices,
            'direction': self.direction,
            'label': self.label,
            'keywords': self.keywords,
            'emoji_hint': self.emoji_hint,
            'raw_line': self.raw_line,
            'setup_type': self.setup_type,
            'profile_name': self.profile_name,
            'bias_note': self.bias_note,
            'active': self.active,
            'confidence_score': self.confidence_score,
            'parsed_metadata': self.parsed_metadata,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None,
            'levels': [level.to_dict() for level in self.levels] if self.levels else []
        }
    
    @classmethod
    def get_active_setups(cls, ticker: Optional[str] = None, trading_day: Optional[date] = None) -> List['TradeSetup']:
        """Get active setups, optionally filtered by ticker and/or trading day."""
        query = cls.query.filter_by(active=True)
        if ticker:
            query = query.filter_by(ticker=ticker.upper())
        if trading_day:
            query = query.filter_by(trading_day=trading_day)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_by_message_id(cls, message_id: str) -> Optional['TradeSetup']:
        """Get setup by Discord message ID."""
        return cls.query.filter_by(message_id=message_id).first()


class ParsedLevel(db.Model):
    """
    New schema model for individual trading levels.
    Stores breakouts, breakdowns, bounces, rejections, targets, etc.
    """
    __tablename__ = "parsing_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to trade setup (updated for string-based ID)
    setup_id = Column(String(50), ForeignKey("trade_setups.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Enhanced level information
    level_type = Column(String(30), nullable=False)  # trigger, target, stop_loss, bias_pivot
    direction = Column(String(10), nullable=True)  # up, down, long, short
    trigger_price = Column(Numeric(12, 4), nullable=False)
    
    # Sequencing and risk management
    sequence_order = Column(Integer, nullable=True)  # 1st, 2nd, 3rd target
    buffer_amount = Column(Numeric(8, 4), nullable=True)  # Stop-loss buffer
    take_profit_percentage = Column(Float, nullable=True)  # 0.33 for 1/3 strategy
    
    # Strategy classification
    strategy = Column(String(20), nullable=True)  # aggressive, conservative, normal
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Additional context
    description = Column(Text, nullable=True)
    level_metadata = Column(JSONB, nullable=True)
    
    # Status
    active = Column(Boolean, default=True)
    triggered = Column(Boolean, default=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    setup = relationship("TradeSetup", back_populates="levels")
    
    def __repr__(self) -> str:
        return f"<ParsedLevel(id={self.id}, level_type={self.level_type}, trigger_price={self.trigger_price})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'setup_id': self.setup_id,
            'level_type': self.level_type,
            'direction': self.direction,
            'trigger_price': float(self.trigger_price) if self.trigger_price is not None else None,
            'strategy': self.strategy,
            'confidence': self.confidence,
            'description': self.description,
            'level_metadata': self.level_metadata,
            'active': self.active,
            'triggered': self.triggered,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None
        }
    
    @classmethod
    def get_by_setup_id(cls, setup_id: int) -> List['ParsedLevel']:
        """Get all levels for a specific setup."""
        return cls.query.filter_by(setup_id=setup_id, active=True).order_by(cls.created_at).all()
    
    @classmethod
    def get_active_levels(cls, level_type: Optional[str] = None) -> List['ParsedLevel']:
        """Get active levels, optionally filtered by type."""
        query = cls.query.filter_by(active=True, triggered=False)
        if level_type:
            query = query.filter_by(level_type=level_type)
        return query.order_by(cls.created_at.desc()).all()


# Legacy model aliases for backward compatibility during migration
SetupModel = TradeSetup