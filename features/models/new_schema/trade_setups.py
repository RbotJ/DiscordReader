"""
New Trade Setups Model

This model stores ticker-wide setup information per trading day.
Part of the new schema restructuring to improve setup parsing and data consistency.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from common.db import db

class TradeSetup(db.Model):
    """
    Trade Setup Model
    
    Stores high-level trading setup information for a specific ticker on a trading day.
    This provides the parent container for individual parsed levels.
    
    Relationships:
    - Many-to-one with DiscordMessage (source message for this setup)
    - One-to-many with ParsedLevel (individual price levels and strategies)
    """
    
    __tablename__ = 'trade_setups'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, doc="Stock ticker symbol (e.g., SPY, TSLA)")
    trade_date = Column(Date, nullable=False, doc="Trading day this setup applies to")
    message_id = Column(String(50), ForeignKey("discord_messages.message_id"), nullable=False, doc="Source Discord message")
    parsed_at = Column(DateTime, default=datetime.utcnow, doc="When this setup was parsed")
    bias_note = Column(Text, nullable=True, doc="Overall market bias or notes for this ticker")
    is_active = Column(Boolean, default=True, doc="Whether this setup is still active")
    
    # Relationships
    message = relationship("DiscordMessage", back_populates="trade_setups")
    parsed_levels = relationship("ParsedLevel", back_populates="setup", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TradeSetup(id={self.id}, ticker='{self.ticker}', trade_date='{self.trade_date}')>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'message_id': self.message_id,
            'parsed_at': self.parsed_at.isoformat() if self.parsed_at else None,
            'bias_note': self.bias_note,
            'is_active': self.is_active,
            'levels_count': len(self.parsed_levels) if self.parsed_levels else 0
        }
    
    def deactivate(self):
        """Mark this setup as inactive"""
        self.is_active = False
        db.session.commit()
    
    @property 
    def levels_summary(self):
        """Get a summary of parsed levels for this setup"""
        if not self.parsed_levels:
            return []
        
        return [{
            'label': level.label,
            'direction': level.direction,
            'trigger_price': level.trigger_price,
            'strategy_type': level.strategy_type
        } for level in self.parsed_levels]