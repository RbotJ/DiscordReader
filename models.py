"""
Database Models for the trading application.

This module defines the SQLAlchemy models for storing trade setups,
signals, and related data in the PostgreSQL database.
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Date, ForeignKey, Text, Enum as SQLEnum,
    JSON
)
from sqlalchemy.orm import relationship, backref
import enum
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
# Define models without circular reference issues

class SetupMessageLegacy(db.Model):
    """Legacy model for trading setup messages (kept for backward compatibility)"""
    __tablename__ = 'setup_messages'
    __table_args__ = {'extend_existing': True}
    __mapper_args__ = {'polymorphic_identity': 'models.SetupMessageLegacy'}
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    raw_text = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, default='unknown')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships - explicitly specify them after both classes are defined
    
    def __repr__(self):
        return f"<SetupMessageLegacy date={self.date} source={self.source}>"
        
# For backward compatibility
SetupMessage = SetupMessageLegacy


class TickerSetupLegacy(db.Model):
    """Legacy model for trading setup for a specific ticker symbol (kept for backward compatibility)"""
    __tablename__ = 'ticker_setups'
    __table_args__ = {'extend_existing': True}
    # Use fully-qualified module name for SQLAlchemy to distinguish between classes
    __mapper_args__ = {'polymorphic_identity': 'models.TickerSetupLegacy'}
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    text = Column(Text, nullable=True)
    message_id = Column(Integer, ForeignKey('setup_messages.id', ondelete='CASCADE'), nullable=False)
    
    # Add discriminator column for model type
    model_type = Column(String(50), nullable=False, default='legacy')
    
    def __repr__(self):
        return f"<TickerSetupLegacy symbol={self.symbol}>"
        
# For backward compatibility
TickerSetup = TickerSetupLegacy

# Relationships will be defined at the end of the file after all models are defined


class Signal(db.Model):
    """Represents a trading signal for a ticker."""
    __tablename__ = 'signals'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    category = Column(SQLEnum(SignalCategoryEnum), nullable=False)
    aggressiveness = Column(SQLEnum(AggressivenessEnum), nullable=False, default=AggressivenessEnum.NONE)
    comparison = Column(SQLEnum(ComparisonTypeEnum), nullable=False)
    # Store trigger as JSON to handle both float and list of floats
    trigger = Column(JSON, nullable=False) 
    targets = Column(JSON, nullable=False)  # Store as JSON array
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
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
    
    # Relationships will be defined after all classes are created
    bias_flip = relationship("BiasFlip", backref="bias", uselist=False, cascade="all, delete-orphan")
    
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
    
    def __repr__(self):
        return f"<BiasFlip direction={self.direction} price={self.price_level}>"


# Define relationships at the end of the file to avoid circular dependencies
# Setup Message -> Ticker Setup relationship
SetupMessageLegacy.ticker_setups = relationship(
    "TickerSetupLegacy",
    primaryjoin="SetupMessageLegacy.id == TickerSetupLegacy.message_id",
    backref="message",
    cascade="all, delete-orphan"
)

# Ticker Setup -> Signal relationship 
Signal.ticker_setup = relationship(
    "TickerSetupLegacy",
    primaryjoin="Signal.ticker_setup_id == TickerSetupLegacy.id",
    backref="signals"
)

# Ticker Setup -> Bias relationship
Bias.ticker_setup = relationship(
    "TickerSetupLegacy",
    primaryjoin="Bias.ticker_setup_id == TickerSetupLegacy.id",
    backref=backref("bias", uselist=False)
)

# Bias -> BiasFlip relationship
Bias.bias_flip = relationship(
    "BiasFlip",
    primaryjoin="Bias.id == BiasFlip.bias_id",
    backref="bias",
    uselist=False,
    cascade="all, delete-orphan"
)