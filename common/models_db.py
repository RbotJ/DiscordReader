"""
Common Database Models

This file contains only truly shared database models and enums that are used across multiple features.
Feature-specific models are now located in their respective feature directories:
- features/setups/models.py - Setup and ticker setup models
- features/strategy/models.py - Signal, bias, and strategy models  
- features/discord/models.py - Discord channel models
- common/events/models.py - Event system models
"""

import enum
from datetime import datetime, date

# --- Shared Enums for Cross-Feature Use ---
class OrderStatus(enum.Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    ACCEPTED_FOR_BIDDING = "accepted_for_bidding"
    STOPPED = "stopped"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    CALCULATED = "calculated"

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class TimeInForce(enum.Enum):
    DAY = "day"
    GTC = "gtc"
    OPG = "opg"
    CLS = "cls"
    IOC = "ioc"
    FOK = "fok"

# No database models in this file - they are now feature-specific
# Import models from their respective feature locations:
# from features.setups.models import SetupMessageModel, TickerSetupModel
# from features.strategy.models import SignalModel, BiasModel, etc.
# from features.discord.models import DiscordChannelModel
# from common.events.models import EventModel