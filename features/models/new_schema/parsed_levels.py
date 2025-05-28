"""
New Parsed Levels Model

This model stores individual parsed setup levels (breakouts, breakdowns, bounces, etc.).
Part of the new schema restructuring to improve setup parsing and data consistency.
"""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from common.db import db

class ParsedLevel(db.Model):
    """
    Parsed Level Model
    
    Stores individual price levels and trading strategies parsed from Discord messages.
    Each level represents a specific trading opportunity (breakout, breakdown, bounce, etc.).
    
    Relationships:
    - Many-to-one with TradeSetup (the parent setup this level belongs to)
    """
    
    __tablename__ = 'parsed_levels'
    
    id = Column(Integer, primary_key=True)
    setup_id = Column(Integer, ForeignKey("trade_setups.id", ondelete="CASCADE"), nullable=False, doc="Parent trade setup")
    label = Column(String, nullable=False, doc="Level label (e.g., 'Aggressive Breakout', 'Conservative Breakdown')")
    direction = Column(String, nullable=False, doc="Trading direction (long/short/bounce/rejection)")
    strategy_type = Column(String, nullable=True, doc="Strategy classification (aggressive/conservative)")
    trigger_relation = Column(String, nullable=False, doc="Price relationship (above/below/near)")
    trigger_price = Column(Float, nullable=False, doc="The key price level that triggers this setup")
    target_1 = Column(Float, nullable=True, doc="First profit target")
    target_2 = Column(Float, nullable=True, doc="Second profit target")  
    target_3 = Column(Float, nullable=True, doc="Third profit target")
    notes = Column(Text, nullable=True, doc="Additional notes or conditions for this level")
    
    # Relationships
    setup = relationship("TradeSetup", back_populates="parsed_levels")
    
    def __repr__(self):
        return f"<ParsedLevel(id={self.id}, label='{self.label}', trigger_price={self.trigger_price})>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'setup_id': self.setup_id,
            'label': self.label,
            'direction': self.direction,
            'strategy_type': self.strategy_type,
            'trigger_relation': self.trigger_relation,
            'trigger_price': self.trigger_price,
            'target_1': self.target_1,
            'target_2': self.target_2,
            'target_3': self.target_3,
            'notes': self.notes
        }
    
    @property
    def targets_list(self):
        """Get list of all non-null targets"""
        targets = []
        if self.target_1 is not None:
            targets.append(self.target_1)
        if self.target_2 is not None:
            targets.append(self.target_2)
        if self.target_3 is not None:
            targets.append(self.target_3)
        return targets
    
    @property
    def is_bullish(self):
        """Check if this level represents a bullish setup"""
        return self.direction.lower() in ['long', 'breakout', 'bounce']
    
    @property
    def is_bearish(self):
        """Check if this level represents a bearish setup"""
        return self.direction.lower() in ['short', 'breakdown', 'rejection']