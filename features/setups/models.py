"""
Setup Models

Database models for trading setups, signals, and related data structures.
"""
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, JSON, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from common.db import db

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Signal types for trading setups."""
    BUY = "buy"
    SELL = "sell"
    LONG = "long"
    SHORT = "short"
    CALL = "call"
    PUT = "put"


class SetupStatus(str, Enum):
    """Status types for trading setups."""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Signal(db.Model):
    """Database model for trading signals."""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id'), nullable=False)
    signal_type = Column(String(50), nullable=False)
    trigger_price = Column(Numeric(10, 2), nullable=True)
    target_price = Column(Numeric(10, 2), nullable=True)
    stop_loss = Column(Numeric(10, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    status = Column(String(50), default=SetupStatus.ACTIVE.value)
    signal_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    ticker_setup = relationship("TickerSetup", back_populates="signals")
    
    def __repr__(self):
        return f"<Signal(id={self.id}, type={self.signal_type}, ticker_setup_id={self.ticker_setup_id})>"


class TickerSetup(db.Model):
    """Database model for ticker-specific trading setups."""
    __tablename__ = 'ticker_setups'
    
    id = Column(Integer, primary_key=True)
    setup_message_id = Column(Integer, ForeignKey('setup_messages.id'), nullable=False)
    symbol = Column(String(10), nullable=False)
    setup_type = Column(String(100), nullable=True)
    direction = Column(String(20), nullable=True)
    entry_price = Column(Numeric(10, 2), nullable=True)
    target_price = Column(Numeric(10, 2), nullable=True)
    stop_loss = Column(Numeric(10, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    status = Column(String(50), default=SetupStatus.ACTIVE.value)
    notes = Column(Text, nullable=True)
    setup_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    setup_message = relationship("SetupMessage", back_populates="ticker_setups")
    signals = relationship("Signal", back_populates="ticker_setup", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TickerSetup(id={self.id}, symbol={self.symbol}, type={self.setup_type})>"
    
    @classmethod
    def get_active_setups(cls, symbol: Optional[str] = None) -> List['TickerSetup']:
        """Get active setups, optionally filtered by symbol."""
        query = cls.query.filter_by(status=SetupStatus.ACTIVE.value)
        if symbol:
            query = query.filter_by(symbol=symbol.upper())
        return query.order_by(cls.created_at.desc()).all()


class SetupMessage(db.Model):
    """Database model for setup messages from Discord."""
    __tablename__ = 'setup_messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True, nullable=False)
    channel_id = Column(String(50), nullable=False)
    author_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=True)
    parsed_date = Column(Date, nullable=True)
    source = Column(String(100), nullable=False)
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default='pending')
    error_message = Column(Text, nullable=True)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker_setups = relationship("TickerSetup", back_populates="setup_message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SetupMessage(id={self.id}, message_id={self.message_id}, processed={self.is_processed})>"
    
    @classmethod
    def get_by_message_id(cls, message_id: str) -> Optional['SetupMessage']:
        """Get setup message by Discord message ID."""
        return cls.query.filter_by(message_id=message_id).first()
    
    @classmethod
    def get_unprocessed_messages(cls) -> List['SetupMessage']:
        """Get all unprocessed setup messages."""
        return cls.query.filter_by(is_processed=False).order_by(cls.created_at.asc()).all()


@dataclass
class SetupDTO:
    """Data transfer object for setup information."""
    symbol: str
    setup_type: Optional[str] = None
    direction: Optional[str] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SignalDTO:
    """Data transfer object for signal information."""
    signal_type: str
    trigger_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SetupMessageDTO:
    """Data transfer object for setup message information."""
    message_id: str
    channel_id: str
    author_id: str
    content: str
    source: str
    parsed_date: Optional[date] = None
    ticker_setups: Optional[List[SetupDTO]] = None
    metadata: Optional[Dict[str, Any]] = None