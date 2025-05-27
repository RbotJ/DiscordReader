"""
Setups Feature Models

Database models for setup messages and ticker setups.
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from common.db import db

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
    signals = relationship("features.strategy.models.SignalModel", back_populates="ticker_setup", cascade="all, delete-orphan")
    bias = relationship("features.strategy.models.BiasModel", back_populates="ticker_setup", uselist=False, cascade="all, delete-orphan")