"""
models_db.py

Consolidated SQLAlchemy database models for the A+ Trading App.
Compatible with vertical-slice architecture and AI-friendly code standards.
"""

import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, JSON,
    DateTime, Date, ForeignKey, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from common.db import db

# --- Enum Definitions ---
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

class OptionsContractType(enum.Enum):
    CALL = "call"
    PUT = "put"

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class OrderTimeInForce(enum.Enum):
    DAY = "day"
    GTC = "gtc"
    OPG = "opg"
    CLS = "cls"
    IOC = "ioc"
    FOK = "fok"

# --- Core Models ---
class SetupMessageModel(db.Model):
    __tablename__ = 'setup_messages'
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), nullable=True)
    source = Column(String(50), nullable=False, default='discord')
    raw_text = Column(Text, nullable=False)
    parsed_data = Column(JSON, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ticker_setups = relationship("TickerSetupModel", back_populates="message", cascade="all, delete-orphan")

class TickerSetupModel(db.Model):
    __tablename__ = 'ticker_setups'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    setup_message_id = Column(Integer, ForeignKey('setup_messages.id', ondelete='CASCADE'), nullable=True)
    text = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    direction = Column(String(10), nullable=True)
    price_level = Column(Float, nullable=True)
    target1 = Column(Float, nullable=True)
    target2 = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    message = relationship("SetupMessageModel", back_populates="ticker_setups")
    signals = relationship("SignalModel", back_populates="ticker_setup", cascade="all, delete-orphan")
    bias = relationship("BiasModel", back_populates="ticker_setup", uselist=False, cascade="all, delete-orphan")

class SignalModel(db.Model):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    category = Column(SQLEnum(SignalCategoryEnum), nullable=False)
    aggressiveness = Column(SQLEnum(AggressivenessEnum), nullable=False, default=AggressivenessEnum.NONE)
    comparison = Column(SQLEnum(ComparisonTypeEnum), nullable=False)
    trigger = Column(JSON, nullable=False)
    targets = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ticker_setup = relationship("TickerSetupModel", back_populates="signals")
    signal_targets = relationship("SignalTargetModel", back_populates="signal", cascade="all, delete-orphan")

class SignalTargetModel(db.Model):
    __tablename__ = 'signal_targets'
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('signals.id', ondelete='CASCADE'), nullable=False)
    price = Column(Float, nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    signal = relationship("SignalModel", back_populates="signal_targets")

class BiasModel(db.Model):
    __tablename__ = 'biases'
    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    direction = Column(SQLEnum(BiasDirectionEnum), nullable=False)
    condition = Column(SQLEnum(ComparisonTypeEnum), nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ticker_setup = relationship("TickerSetupModel", back_populates="bias")
    bias_flip = relationship("BiasFlipModel", back_populates="bias", uselist=False, cascade="all, delete-orphan")

class BiasFlipModel(db.Model):
    __tablename__ = 'bias_flips'
    id = Column(Integer, primary_key=True)
    bias_id = Column(Integer, ForeignKey('biases.id', ondelete='CASCADE'), nullable=False)
    direction = Column(SQLEnum(BiasDirectionEnum), nullable=False)
    price_level = Column(Float, nullable=False)

    bias = relationship("BiasModel", back_populates="bias_flip")

class DiscordChannelModel(db.Model):
    """Discord channel model for multi-channel management."""
    __tablename__ = 'discord_channels'

    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), nullable=False)
    channel_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    channel_type = Column(String(50), nullable=False, default='text')
    is_listen = Column(Boolean, nullable=False, default=False)
    is_announce = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('guild_id', 'channel_id', name='_guild_channel_uc'),)

    def __repr__(self):
        return f"<DiscordChannel(id={self.id}, name='{self.name}', channel_id='{self.channel_id}')>"

class EventModel(db.Model):
    """Event model for logging structured events in PostgreSQL."""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False, index=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Event(channel={self.channel}, created_at={self.created_at})>"
