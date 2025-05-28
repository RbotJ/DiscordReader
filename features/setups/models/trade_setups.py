"""
Trade Setups Model

This model represents ticker-wide trading setups parsed from Discord messages,
storing one record per ticker per trading day.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Text, Boolean, DateTime, ForeignKey
from common.db import db

class TradeSetup(db.Model):
    """
    High-level trading setup for a specific ticker on a trading day.
    
    This table stores one record per ticker per day, representing the overall
    trading setup and bias for that ticker, with individual price levels
    stored in the ParsedLevel table.
    """
    __tablename__ = 'trade_setups_new'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False,
                   doc="Stock ticker symbol (e.g., SPY, TSLA, NVDA)")
    trade_date = Column(Date, nullable=False,
                       doc="Trading day this setup applies to")
    message_id = Column(String(50), ForeignKey("discord_messages_new.message_id"), nullable=False,
                       doc="Source Discord message containing this setup")
    parsed_at = Column(DateTime, default=datetime.utcnow,
                      doc="When this setup was parsed from the message")
    bias_note = Column(Text, nullable=True,
                      doc="Overall market bias or notes for this ticker")
    is_active = Column(Boolean, default=True,
                      doc="Whether this setup is still active for trading")

    def __repr__(self):
        return f"<TradeSetup {self.ticker} on {self.trade_date}>"