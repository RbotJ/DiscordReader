"""
Strategy Feature Models

Database models for signals, biases, and strategy-related data.
"""

import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import ENUM as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from common.db import db

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

    ticker_setup = relationship("features.setups.models.TickerSetupModel", back_populates="signals")
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

    ticker_setup = relationship("features.setups.models.TickerSetupModel", back_populates="bias")
    bias_flip = relationship("BiasFlipModel", back_populates="bias", uselist=False, cascade="all, delete-orphan")

class BiasFlipModel(db.Model):
    __tablename__ = 'bias_flips'
    id = Column(Integer, primary_key=True)
    bias_id = Column(Integer, ForeignKey('biases.id', ondelete='CASCADE'), nullable=False)
    direction = Column(SQLEnum(BiasDirectionEnum), nullable=False)
    price_level = Column(Float, nullable=False)

    bias = relationship("BiasModel", back_populates="bias_flip")