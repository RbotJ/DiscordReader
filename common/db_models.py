"""
Database Models

This module contains SQLAlchemy models for the trading application's database.
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from common.db import db

class EventModel(db.Model):
    """Model for storing events in the database."""
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    channel = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            'id': self.id,
            'channel': self.channel,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DiscordMessageModel(db.Model):
    """Model for storing Discord messages."""
    __tablename__ = 'discord_messages'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(50), nullable=False, index=True)
    message_id = Column(String(50), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'message_id': self.message_id,
            'content': self.content,
            'author': self.author,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TradeModel(db.Model):
    """Model for storing trade data."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default='executed')
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status
        }

class TickerModel(db.Model):
    """Model for storing ticker data."""
    __tablename__ = 'tickers'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True, unique=True)
    name = Column(String(100), nullable=True)
    last_price = Column(Float, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'last_price': self.last_price,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SetupModel(db.Model):
    """Model for storing trading setups."""
    __tablename__ = 'setups'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    message_id = Column(String(50), nullable=True, index=True)
    setup_type = Column(String(50), nullable=False)
    price_level = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'message_id': self.message_id,
            'setup_type': self.setup_type,
            'price_level': self.price_level,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }