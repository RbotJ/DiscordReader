"""
Constants and Enums

Split from legacy event_constants.py. This file includes:
- Market hours
- Risk configuration
- Relevant enums for internal application logic
"""

from enum import Enum

# --- Market Hours (Eastern Time) ---
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# --- Risk Configuration ---
DEFAULT_RISK_AMOUNT = 500.0  # Maximum risk per position in dollars
DEFAULT_POSITION_SIZE = 1    # Default number of contracts/shares
MAX_POSITIONS = 5            # Max number of concurrent positions

# --- Enums ---
class SignalState(str, Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class SignalEvent(str, Enum):
    ADDED = "added"
    UPDATED = "updated"
    TRIGGERED = "trigger"
    TARGET_HIT = "target_hit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"

class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"

class Timeframe(str, Enum):
    ONE_MINUTE = "1Min"
    FIVE_MINUTES = "5Min"
    FIFTEEN_MINUTES = "15Min"
    ONE_HOUR = "1Hour"
    ONE_DAY = "1Day"
