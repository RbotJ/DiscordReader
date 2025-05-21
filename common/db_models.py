"""
Database models for A+ Trading App.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app import db


class SetupModel(db.Model):
    """Setup message from A+ Trading."""
    __tablename__ = 'setups'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    raw_text = Column(Text, nullable=False)
    source = Column(String(50), default='unknown')
    created_at = Column(DateTime, default=datetime.utcnow)
    parsed = Column(Boolean, default=False)
    
    # Relationships
    ticker_setups = relationship('TickerSetupModel', back_populates='setup', cascade='all, delete-orphan')


class TickerSetupModel(db.Model):
    """Ticker setup extracted from a setup message."""
    __tablename__ = 'ticker_setups'
    
    id = Column(Integer, primary_key=True)
    setup_id = Column(Integer, ForeignKey('setups.id', ondelete='CASCADE'), nullable=False)
    symbol = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    setup = relationship('SetupModel', back_populates='ticker_setups')
    signals = relationship('SignalModel', back_populates='ticker_setup', cascade='all, delete-orphan')
    bias = relationship('BiasModel', back_populates='ticker_setup', cascade='all, delete-orphan', uselist=False)


class SignalModel(db.Model):
    """Trading signal extracted from a ticker setup."""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    category = Column(String(20), nullable=False)  # breakout, breakdown, rejection, bounce
    aggressiveness = Column(String(10), default='none')  # none, low, medium, high
    comparison = Column(String(10), nullable=False)  # above, below, near, range
    trigger_value = Column(JSON, nullable=False)  # single value or array for range
    targets = Column(JSON, nullable=False)  # array of target price levels
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    
    # Relationships
    ticker_setup = relationship('TickerSetupModel', back_populates='signals')
    price_triggers = relationship('PriceTriggerModel', back_populates='signal', cascade='all, delete-orphan')
    orders = relationship('OrderModel', back_populates='signal')


class BiasModel(db.Model):
    """Market bias for a ticker setup."""
    __tablename__ = 'biases'
    
    id = Column(Integer, primary_key=True)
    ticker_setup_id = Column(Integer, ForeignKey('ticker_setups.id', ondelete='CASCADE'), nullable=False)
    direction = Column(String(10), nullable=False)  # bullish, bearish
    condition = Column(String(10), nullable=False)  # above, below, near, range
    price = Column(Float, nullable=False)
    flip_direction = Column(String(10), nullable=True)  # bullish, bearish
    flip_price_level = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticker_setup = relationship('TickerSetupModel', back_populates='bias')


class OptionsContractModel(db.Model):
    """Options contract data."""
    __tablename__ = 'options_contracts'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False)
    underlying = Column(String(10), nullable=False, index=True)
    expiration_date = Column(Date, nullable=False, index=True)
    strike = Column(Float, nullable=False)
    option_type = Column(String(4), nullable=False)  # call, put
    last_update = Column(DateTime, default=datetime.utcnow)
    
    # Market data
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    last = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    
    # Greeks
    implied_volatility = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    rho = Column(Float, nullable=True)


class OrderModel(db.Model):
    """Trade order data."""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    alpaca_order_id = Column(String(50), nullable=True)
    client_order_id = Column(String(50), nullable=False)
    signal_id = Column(Integer, ForeignKey('signals.id'), nullable=True)
    symbol = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    side = Column(String(5), nullable=False)  # buy, sell
    type = Column(String(10), nullable=False)  # market, limit, stop
    time_in_force = Column(String(5), nullable=False)  # day, gtc
    limit_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    status = Column(String(20), nullable=False)  # submitted, filled, partial, canceled, rejected
    filled_qty = Column(Integer, default=0)
    filled_avg_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    signal = relationship('SignalModel', back_populates='orders')


class PositionModel(db.Model):
    """Trading position data."""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    side = Column(String(5), nullable=False)  # long, short
    market_value = Column(Float, nullable=True)
    cost_basis = Column(Float, nullable=True)
    unrealized_pl = Column(Float, nullable=True)
    unrealized_plpc = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    lastday_price = Column(Float, nullable=True)
    change_today = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class PriceTriggerModel(db.Model):
    """Price trigger for a signal."""
    __tablename__ = 'price_triggers'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    comparison = Column(String(10), nullable=False)  # above, below, near, range
    trigger_value = Column(JSON, nullable=False)  # single value or range
    signal_id = Column(Integer, ForeignKey('signals.id', ondelete='CASCADE'), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    
    # Relationships
    signal = relationship('SignalModel', back_populates='price_triggers')


class MarketDataModel(db.Model):
    """Market data for a symbol."""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    previous_close = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint for symbol and timestamp
    __table_args__ = (
        db.UniqueConstraint('symbol', 'timestamp', name='uix_market_data_symbol_timestamp'),
    )


class WatchlistModel(db.Model):
    """Watchlist of symbols to monitor."""
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True)
    added_at = Column(DateTime, default=datetime.utcnow)


class NotificationModel(db.Model):
    """User notification for trading events."""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(20), nullable=False)  # signal, trade, price, system
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)  # renamed from metadata which is reserved in SQLAlchemy
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)