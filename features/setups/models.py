"""
Setup Models Module

This module defines the database models for trading setups, signals, and related entities.
"""
import enum
from datetime import datetime, date
from common.db import db

# Define Enum types - these will be stored as strings in the database
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
    __tablename__ = 'setups'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    raw_text = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    
    # Relationships
    ticker_setups = db.relationship("TickerSetup", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SetupMessage date={self.date} source={self.source}>"


class TickerSetup(db.Model):
    """Represents a trading setup for a specific ticker symbol."""
    __tablename__ = 'ticker_setups'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    text = db.Column(db.Text, nullable=True)
    setup_id = db.Column(db.Integer, db.ForeignKey('setups.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    message = db.relationship("SetupMessage", foreign_keys=[setup_id], back_populates="ticker_setups")
    signals = db.relationship("Signal", back_populates="ticker_setup", cascade="all, delete-orphan")
    bias = db.relationship("Bias", back_populates="ticker_setup", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TickerSetup symbol={self.symbol}>"


class Signal(db.Model):
    """Represents a trading signal for a ticker."""
    __tablename__ = 'signals'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker_setup_id = db.Column(db.Integer, db.ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    aggressiveness = db.Column(db.String(10), nullable=True)
    comparison = db.Column(db.String(10), nullable=False)
    
    # Store trigger and targets as JSON in the database
    trigger_value = db.Column(db.JSON, nullable=False)  # JSON representation
    targets = db.Column(db.JSON, nullable=False)        # JSON array
    
    active = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)
    triggered_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    ticker_setup = db.relationship("TickerSetup", back_populates="signals")
    signal_targets = db.relationship("SignalTarget", back_populates="signal", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Signal category={self.category}>"


class SignalTarget(db.Model):
    """Represents a price target for a signal."""
    __tablename__ = 'signal_targets'
    
    id = db.Column(db.Integer, primary_key=True)
    signal_id = db.Column(db.Integer, db.ForeignKey('signals.id', ondelete='CASCADE'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    signal = db.relationship("Signal", back_populates="signal_targets")
    
    def __repr__(self):
        return f"<SignalTarget price={self.price} position={self.position}>"


class Bias(db.Model):
    """Represents a market bias for a ticker."""
    __tablename__ = 'biases'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker_setup_id = db.Column(db.Integer, db.ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'bullish' or 'bearish'
    condition = db.Column(db.String(10), nullable=False)  # 'above', 'below', 'near', 'range'
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=True)
    
    # Optional fields for flip price
    flip_direction = db.Column(db.String(10), nullable=True)  # 'bullish' or 'bearish'
    flip_price_level = db.Column(db.Float, nullable=True)
    
    # Relationships
    ticker_setup = db.relationship("TickerSetup", back_populates="bias")
    
    def __repr__(self):
        flip_info = f", flip={self.flip_direction} at {self.flip_price_level}" if self.flip_direction else ""
        return f"<Bias direction={self.direction} price={self.price}{flip_info}>"