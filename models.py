"""
Setup Models Module

This module defines the database models for trading setups, signals, and related entities.
"""
import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Date, ForeignKey, Text, Enum as SQLEnum,
    JSON
)
from sqlalchemy.orm import relationship, backref
from common.db import db

# Define Enum types
class SignalCategoryEnum(enum.Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    REJECTION = "rejection"
    BOUNCE = "bounce"

class AggressivenessEnum(enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"

class ComparisonTypeEnum(enum.Enum):
    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"
    RANGE = "range"

class BiasDirectionEnum(enum.Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"

# Database Models
class SetupMessage(db.Model):
    """Represents a trading setup message containing one or more ticker setups."""
    __tablename__ = 'setup_messages'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, default='discord')
    message_id = Column(String(50), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Define relationship to ticker_setups
    ticker_setups = relationship(
        "TickerSetup",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SetupMessage date={self.date} source={self.source}>"


class TickerSetup(db.Model):
    """Represents a trading setup for a specific ticker symbol."""
    __tablename__ = 'ticker_setups'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    text = Column(Text, nullable=True)
    message_id = Column(Integer, ForeignKey('setup_messages.id', ondelete='CASCADE'), nullable=False)
    model_type = Column(String(50), nullable=False, default='new')

    # Define relationships
    message = relationship(
        "SetupMessage",
        back_populates="ticker_setups",
        foreign_keys=[message_id]
    )

    signals = relationship(
        "Signal",
        back_populates="ticker_setup",
        cascade="all, delete-orphan"
    )

    bias = relationship(
        "Bias",
        back_populates="ticker_setup",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TickerSetup symbol={self.symbol}>"


class Signal(db.Model):
    """Represents a trading signal for a ticker."""
    __tablename__ = 'signals'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    category = Column(SQLEnum(SignalCategoryEnum), nullable=False)
    aggressiveness = Column(SQLEnum(AggressivenessEnum), nullable=False, default=AggressivenessEnum.NONE)
    comparison = Column(SQLEnum(ComparisonTypeEnum), nullable=False)
    trigger = Column(JSON, nullable=False)  # Store as JSON to handle both float and list
    targets = Column(JSON, nullable=False)  # Store as JSON array
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Define relationship to ticker_setup
    ticker_setup = relationship(
        "TickerSetup",
        back_populates="signals",
        foreign_keys=[ticker_setup_id]
    )

    def __repr__(self):
        return f"<Signal category={self.category} trigger={self.trigger}>"


class Bias(db.Model):
    """Represents a market bias for a ticker."""
    __tablename__ = 'biases'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    direction = Column(SQLEnum(BiasDirectionEnum), nullable=False)
    condition = Column(SQLEnum(ComparisonTypeEnum), nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Define relationship to ticker_setup
    ticker_setup = relationship(
        "TickerSetup",
        back_populates="bias",
        foreign_keys=[ticker_setup_id]
    )

    # Define relationship to bias_flip
    bias_flip = relationship(
        "BiasFlip",
        uselist=False,
        back_populates="bias",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Bias direction={self.direction} price={self.price}>"


class BiasFlip(db.Model):
    """Represents a bias flip condition."""
    __tablename__ = 'bias_flips'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    bias_id = Column(Integer, ForeignKey('biases.id', ondelete='CASCADE'), nullable=False)
    direction = Column(SQLEnum(BiasDirectionEnum), nullable=False)
    price_level = Column(Float, nullable=False)

    # Define relationship to bias
    bias = relationship(
        "Bias",
        back_populates="bias_flip",
        foreign_keys=[bias_id]
    )

    def __repr__(self):
        return f"<BiasFlip direction={self.direction} price={self.price_level}>"