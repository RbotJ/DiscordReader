"""
Breakout Trade Setup Confirmation Module

This module monitors for breakout trade setup confirmations based on price and volume conditions.
It analyzes real-time 5-minute candle data to confirm when a breakout occurs, publishing
confirmation events to the PostgreSQL event system.
"""

import logging
import asyncio
from datetime import datetime, time
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple, Set, Union

from common.events.publisher import publish_event
from common.events.constants import EventTypes, EventChannels
from features.setups.enhanced_parser import Signal, extract_unique_levels

# Configure logger
logger = logging.getLogger(__name__)

# Constants for confirmation thresholds
DEFAULT_MIN_BODY_PERCENT = 0.2  # Minimum candle body size as percentage
DEFAULT_VOLUME_MULTIPLIER = 1.5  # Minimum volume relative to average
DEFAULT_AVG_VOLUME_PERIODS = 5   # Number of periods for volume average

# Confirmation tracking to avoid duplicate alerts
_confirmed_signals = set()  # Set of confirmed signal IDs

class Candle:
    """Simple candle data structure with OHLCV data"""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize a candle from dictionary data.

        Args:
            data: Dictionary with 't', 'o', 'h', 'l', 'c', 'v' fields
        """
        self.timestamp = data.get('t')
        if isinstance(self.timestamp, str):
            # Convert ISO format timestamp to datetime if needed
            try:
                self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except ValueError:
                # Handle other timestamp formats here if needed
                pass

        self.open = float(data.get('o', 0))
        self.high = float(data.get('h', 0))
        self.low = float(data.get('l', 0))
        self.close = float(data.get('c', 0))
        self.volume = float(data.get('v', 0))

    @property
    def body_size(self) -> float:
        """
        Get the absolute size of the candle body.

        Returns:
            float: Absolute difference between open and close
        """
        return abs(self.close - self.open)

    @property
    def body_percent(self) -> float:
        """
        Get the candle body size as a percentage of price.

        Returns:
            float: Body size as percentage of open price
        """
        if self.open == 0:
            return 0
        return (self.body_size / self.open) * 100

    @property
    def is_bullish(self) -> bool:
        """
        Check if the candle is bullish (close > open).

        Returns:
            bool: True if bullish, False if bearish
        """
        return self.close > self.open

    @property
    def range(self) -> float:
        """
        Get the full range of the candle (high - low).

        Returns:
            float: Candle range
        """
        return self.high - self.low

def is_market_hours(timestamp: datetime) -> bool:
    """
    Check if the timestamp is during market hours (9:30 AM - 4:00 PM Eastern Time).

    Args:
        timestamp: Datetime to check

    Returns:
        bool: True if during market hours, False otherwise
    """
    # For now, use a simple check based on hour (should be expanded with timezone)
    if timestamp is None:
        return False

    hour = timestamp.hour
    minute = timestamp.minute

    # Check if time is between 9:30 AM and 4:00 PM
    if hour < 9 or hour > 16:
        return False
    if hour == 9 and minute < 30:
        return False

    return True

def is_confirmed_breakout(
    candle: Candle,
    signal: Signal,
    avg_volume: Optional[float] = None,
    previous_candles: Optional[List[Candle]] = None,
    min_body_percent: float = DEFAULT_MIN_BODY_PERCENT,
    volume_multiplier: float = DEFAULT_VOLUME_MULTIPLIER,
    check_market_hours: bool = True
) -> bool:
    """
    Check if a candle confirms a breakout trade setup.

    Args:
        candle: The candle to check
        signal: The signal to confirm
        avg_volume: Optional pre-computed average volume
        previous_candles: Optional list of previous candles to calculate average volume
        min_body_percent: Minimum candle body size as percentage for confirmation
        volume_multiplier: Volume must be this multiple of average volume
        check_market_hours: If True, only confirm during market hours

    Returns:
        bool: True if confirmed, False otherwise
    """
    # Only process breakout signals
    if signal.type != "breakout":
        return False

    # 1. Check if close is above the trigger level
    if candle.close <= signal.trigger:
        return False

    # 2. Check if the candle is bullish
    if not candle.is_bullish:
        return False

    # 3. Check if the candle body is large enough
    if candle.body_percent < min_body_percent:
        return False

    # 4. Optional market hours check
    if check_market_hours and not is_market_hours(candle.timestamp):
        return False

    # 5. Volume check
    # If average volume not provided, calculate from previous candles
    if avg_volume is None and previous_candles:
        if len(previous_candles) > 0:
            avg_volume = sum(c.volume for c in previous_candles) / len(previous_candles)
        else:
            avg_volume = 0

    # Skip volume check if we couldn't calculate average
    if avg_volume is not None and avg_volume > 0:
        if candle.volume < avg_volume * volume_multiplier:
            return False

    # All conditions passed, confirm the breakout
    return True

def calculate_average_volume(candles: List[Candle], periods: int = DEFAULT_AVG_VOLUME_PERIODS) -> float:
    """
    Calculate the average volume over a number of periods.

    Args:
        candles: List of candles to calculate from
        periods: Number of periods to average

    Returns:
        float: Average volume
    """
    if not candles:
        return 0

    # Take the most recent n candles
    recent_candles = candles[-periods:] if len(candles) > periods else candles

    # Calculate the average
    return sum(c.volume for c in recent_candles) / len(recent_candles)

async def monitor_signals(
    candles: AsyncGenerator[Dict[str, Any], None],
    signals: List[Signal],
    avg_volume_periods: int = DEFAULT_AVG_VOLUME_PERIODS,
    min_body_percent: float = DEFAULT_MIN_BODY_PERCENT,
    volume_multiplier: float = DEFAULT_VOLUME_MULTIPLIER
) -> None:
    """
    Monitor signals against a stream of candle data.

    Args:
        candles: Async generator yielding candle data
        signals: List of signals to monitor
        avg_volume_periods: Number of periods for volume average
        min_body_percent: Minimum candle body size as percentage
        volume_multiplier: Volume must be this multiple of average volume
    """
    # Group signals by ticker for efficient processing
    ticker_signals = {}
    for signal in signals:
        ticker = signal.setup_id.split('-')[0] if isinstance(signal.setup_id, str) else "unknown"
        if ticker not in ticker_signals:
            ticker_signals[ticker] = []
        ticker_signals[ticker].append(signal)

    # Keep track of previous candles for each ticker to calculate volume averages
    ticker_candles: Dict[str, List[Candle]] = {}

    # Process candles as they come in
    try:
        async for candle_data in candles:
            # Extract ticker and create Candle object
            ticker = candle_data.get('ticker')
            if not ticker:
                logger.warning(f"Received candle without ticker: {candle_data}")
                continue

            # Create a Candle object from the data
            candle = Candle(candle_data)

            # Initialize candle list for this ticker if needed
            if ticker not in ticker_candles:
                ticker_candles[ticker] = []

            # Add this candle to the history
            ticker_candles[ticker].append(candle)

            # Keep only the most recent 20 candles (more than we need for avg volume)
            ticker_candles[ticker] = ticker_candles[ticker][-20:]

            # Calculate average volume for this ticker
            avg_volume = calculate_average_volume(
                ticker_candles[ticker],
                periods=avg_volume_periods
            )

            # Skip if no signals for this ticker
            if ticker not in ticker_signals:
                continue

            # Check each signal for this ticker
            for signal in ticker_signals[ticker]:
                # Skip if already confirmed
                if signal.id in _confirmed_signals:
                    continue

                # Skip non-breakout signals
                if signal.type != "breakout":
                    continue

                # Check if this candle confirms the breakout
                previous_candles = ticker_candles[ticker][:-1]  # All except current

                if is_confirmed_breakout(
                    candle=candle,
                    signal=signal,
                    avg_volume=avg_volume,
                    previous_candles=previous_candles,
                    min_body_percent=min_body_percent,
                    volume_multiplier=volume_multiplier
                ):
                    # Mark as confirmed to avoid duplicate alerts
                    _confirmed_signals.add(signal.id)

                    # Log the confirmation
                    logger.info(
                        f"CONFIRMED BREAKOUT: {ticker} above {signal.trigger:.2f} "
                        f"(close: {candle.close:.2f}, vol: {candle.volume:.0f} vs avg: {avg_volume:.0f})"
                    )

                    # Update the signal in place
                    signal.confirmed = True
                    signal.confirmed_at = datetime.now()
                    signal.confirmation_details = {
                        "price": candle.close,
                        "volume": candle.volume,
                        "avg_volume": avg_volume,
                        "body_percent": candle.body_percent,
                        "timestamp": candle.timestamp.isoformat() if isinstance(candle.timestamp, datetime) else candle.timestamp
                    }

                    # Publish confirmation event
                    publish_confirmation_event(signal, candle, avg_volume)

    except Exception as e:
        logger.error(f"Error in signal monitor: {e}")
        raise

def publish_confirmation_event(signal: Signal, candle: Candle, avg_volume: float) -> bool:
    """
    Publish a confirmation event to the event system.

    Args:
        signal: The signal that was confirmed
        candle: The candle that confirmed the signal
        avg_volume: The average volume used for confirmation

    Returns:
        bool: Success status
    """
    # Create event data
    event_data = {
        'event_type': 'signal.confirmed',
        'ticker': signal.setup_id.split('-')[0] if isinstance(signal.setup_id, str) else "unknown",
        'signal_id': signal.id,
        'setup_id': signal.setup_id,
        'signal_type': signal.type,
        'direction': signal.direction,
        'aggressiveness': signal.aggressiveness,
        'level': signal.trigger,
        'confirmation': {
            'timestamp': candle.timestamp.isoformat() if isinstance(candle.timestamp, datetime) else candle.timestamp,
            'price': candle.close,
            'volume': candle.volume,
            'avg_volume': avg_volume,
            'body_percent': candle.body_percent
        },
        'targets': signal.targets
    }

    # Publish to the event system
    return event_client.publish_event(EventChannels.SIGNAL_TRIGGERED, event_data)

def clear_confirmed_signals() -> None:
    """Clear the confirmed signals tracking set (for testing)."""
    _confirmed_signals.clear()