"""
Database Models

This module defines the SQLAlchemy models for the trading application.
"""
import enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from common.db import db

class DiscordMessageModel(db.Model):
    """Discord message model for storing messages from Discord."""
    __tablename__ = 'discord_messages'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), nullable=False, index=True)
    channel_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<DiscordMessage(id={self.id}, message_id={self.message_id})>"

class EventModel(db.Model):
    """Event model for storing events in the event system."""
    __tablename__ = 'events'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    channel = Column(String(50), nullable=False, index=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Event(id={self.id}, channel={self.channel})>"

class SetupModel(db.Model):
    """Trading setup model."""
    __tablename__ = 'setups'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False)
    entry_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    direction = Column(String(10), nullable=True)  # 'long' or 'short'
    status = Column(String(20), nullable=False, default='pending')
    source = Column(String(20), nullable=False, default='discord')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Setup(id={self.id}, ticker={self.ticker}, date={self.date})>"

class SignalModel(db.Model):
    """Trading signal model."""
    __tablename__ = 'signals'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    setup_id = Column(Integer, ForeignKey('setups.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(20), nullable=False)  # 'breakout', 'rejection', etc.
    price = Column(Float, nullable=False)
    triggered = Column(Boolean, default=False, nullable=False)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    setup = relationship("SetupModel", backref="signals")
    
    def __repr__(self):
        return f"<Signal(id={self.id}, type={self.type}, price={self.price})>"

class TradeModel(db.Model):
    """Trade execution model."""
    __tablename__ = 'trades'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    setup_id = Column(Integer, ForeignKey('setups.id'), nullable=True)
    ticker = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # 'buy' or 'sell'
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    order_id = Column(String(50), nullable=True)
    filled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    setup = relationship("SetupModel", backref="trades")
    
    def __repr__(self):
        return f"<Trade(id={self.id}, ticker={self.ticker}, side={self.side})>"