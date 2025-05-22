"""
Database Models

This module defines the SQLAlchemy models for the trading application.
"""
import enum
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from common.db import db

# Enum definitions for use in models
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
        
class OrderModel(db.Model):
    """Order execution model for Alpaca API integration."""
    __tablename__ = 'orders'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    setup_id = Column(Integer, ForeignKey('setups.id'), nullable=True)
    ticker = Column(String(10), nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    type = Column(SQLEnum(OrderType), nullable=False, default=OrderType.MARKET)
    time_in_force = Column(SQLEnum(OrderTimeInForce), nullable=False, default=OrderTimeInForce.DAY)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Only for limit orders
    stop_price = Column(Float, nullable=True)  # Only for stop orders
    status = Column(String(20), nullable=False, default='pending')
    alpaca_order_id = Column(String(50), nullable=True)
    filled_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    setup = relationship("SetupModel", backref="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, ticker={self.ticker}, side={self.side}, status={self.status})>"
        
class MarketDataModel(db.Model):
    """Market data model for storing real-time and historical market data."""
    __tablename__ = 'market_data'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    vwap = Column(Float, nullable=True)
    data_source = Column(String(20), nullable=False, default='alpaca')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<MarketData(ticker={self.ticker}, date={self.date}, close={self.close})>"
        
class OptionsContractModel(db.Model):
    """Options contract model for storing options contract data."""
    __tablename__ = 'options_contracts'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, index=True)
    contract_type = Column(SQLEnum(OptionsContractType), nullable=False)
    expiration_date = Column(Date, nullable=False, index=True)
    strike_price = Column(Float, nullable=False)
    last_price = Column(Float, nullable=True)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    open_interest = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<OptionsContract(ticker={self.ticker}, type={self.contract_type}, strike={self.strike_price}, exp={self.expiration_date})>"
        
class TickerModel(db.Model):
    """Ticker model for storing ticker symbols and metadata."""
    __tablename__ = 'tickers'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    company_name = Column(String(100), nullable=True)
    sector = Column(String(50), nullable=True)
    industry = Column(String(50), nullable=True)
    exchange = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_etf = Column(Boolean, nullable=False, default=False)
    is_watchlist = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Ticker(symbol={self.symbol}, name={self.company_name})>"
        
class TickerSetupModel(db.Model):
    """Extended ticker setup model with additional fields."""
    __tablename__ = 'ticker_setups'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    setup_message_id = Column(Integer, ForeignKey('setup_messages.id', ondelete='CASCADE'), nullable=True)
    text = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # 'breakout', 'rejection', etc.
    price_level = Column(Float, nullable=True)
    direction = Column(String(10), nullable=True)  # 'bullish', 'bearish'
    target1 = Column(Float, nullable=True)
    target2 = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TickerSetup(id={self.id}, symbol={self.symbol}, category={self.category})>"
        
class PositionModel(db.Model):
    """Position model for tracking open positions."""
    __tablename__ = 'positions'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    unrealized_pl = Column(Float, nullable=True)
    realized_pl = Column(Float, nullable=True)
    side = Column(String(10), nullable=False)  # 'long' or 'short'
    status = Column(String(20), nullable=False, default='open')
    setup_id = Column(Integer, ForeignKey('setups.id'), nullable=True)
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    setup = relationship("SetupModel", backref="positions")
    
    def __repr__(self):
        return f"<Position(id={self.id}, ticker={self.ticker}, quantity={self.quantity}, side={self.side})>"
        
class WatchlistModel(db.Model):
    """Watchlist model for tracking tickers of interest."""
    __tablename__ = 'watchlists'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Watchlist(id={self.id}, name={self.name}, ticker={self.ticker})>"
        
class CandleModel(db.Model):
    """Candle model for storing candle pattern detections."""
    __tablename__ = 'candles'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False)  # 'engulfing', 'doji', etc.
    direction = Column(String(10), nullable=False)  # 'bullish' or 'bearish'
    strength = Column(Float, nullable=True)  # 0.0 to 1.0
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Candle(id={self.id}, ticker={self.ticker}, pattern={self.pattern_type}, direction={self.direction})>"