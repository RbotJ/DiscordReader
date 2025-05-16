"""
Candle-based Strategy Detector

This module enhances the strategy detector with candle pattern recognition
and confirmation capabilities, processing full candle closes to generate
trade signals.
"""
import os
import logging
import threading
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from app import app, db
from models import SignalCategoryEnum, ComparisonTypeEnum, BiasDirectionEnum
from common.redis_utils import RedisClient, get_redis_client
from common.constants import (
    CANDLE_UPDATE_CHANNEL,
    TICKER_SIGNAL_CHANNEL,
    STRATEGY_CHANNEL
)

# Configure logger
logger = logging.getLogger(__name__)

# Redis client
redis_client = get_redis_client()

# Constants
CANDLE_CONFIRMATION_REQUIRED = True   # Require full candle close for confirmation
DEFAULT_ENTRY_TIMEFRAME = "5m"       # Default timeframe for entry confirmation
BIAS_PIVOT_BUFFER = 0.001            # 0.1% buffer for bias pivot levels
VOLUME_SPIKE_THRESHOLD = 1.5         # 50% above average volume considered a spike
FAST_MA_PERIOD = 9                   # Fast moving average period


class SignalStatus(Enum):
    """Signal status enum."""
    WATCHING = "watching"         # Watching for trigger
    TRIGGERED = "triggered"       # Price crossed trigger level
    CONFIRMED = "confirmed"       # Candle close confirmed the trigger
    EXECUTED = "executed"         # Trade executed
    COMPLETED = "completed"       # All targets hit or stopped out
    CANCELLED = "cancelled"       # Signal cancelled


@dataclass
class Candle:
    """Candle data structure."""
    timestamp: datetime
    open: float
    high: float
    close: float
    low: float
    volume: float


@dataclass
class Signal:
    """Trading signal data structure."""
    id: int
    symbol: str
    category: str  
    comparison: str
    trigger_value: float
    targets: List[float]
    bias_direction: str = None
    bias_level: float = None
    bias_flip_direction: str = None
    bias_flip_level: float = None
    stop_level: float = None
    entry_level: float = None
    entry_timeframe: str = DEFAULT_ENTRY_TIMEFRAME
    status: str = SignalStatus.WATCHING.value
    confirmation_candle: Candle = None
    last_update: datetime = None
    position_size: int = 1  # Default to 1 contract


class CandleDetector:
    """Candle pattern detector for confirming trading signals."""
    
    def __init__(self):
        """Initialize the candle detector."""
        self.active_signals = {}  # symbol -> list of signals
        self.candle_cache = {}    # symbol-timeframe -> list of candles
        self.running = False
        self.lock = threading.Lock()
    
    def start(self):
        """Start the candle detector."""
        if self.running:
            return
        
        self.running = True
        logger.info("Candle detector started")
        
        # Subscribe to candle updates
        if redis_client and redis_client.available:
            redis_client.subscribe(CANDLE_UPDATE_CHANNEL, self._handle_candle_update)
            logger.info(f"Subscribed to candle updates on {CANDLE_UPDATE_CHANNEL}")
        else:
            logger.warning("Redis not available, candle updates will not be processed")
    
    def stop(self):
        """Stop the candle detector."""
        if not self.running:
            return
        
        self.running = False
        
        # Unsubscribe from candle updates
        if redis_client and redis_client.available:
            redis_client.unsubscribe(CANDLE_UPDATE_CHANNEL)
        
        logger.info("Candle detector stopped")
    
    def add_signal(self, signal_data: Dict[str, Any]) -> Signal:
        """
        Add a signal to be monitored by the candle detector.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            Signal object
        """
        with self.lock:
            # Create signal object
            signal = Signal(
                id=signal_data["id"],
                symbol=signal_data["symbol"],
                category=signal_data["category"],
                comparison=signal_data["comparison"],
                trigger_value=float(signal_data["trigger_value"]),
                targets=[float(t) for t in signal_data["targets"]],
                bias_direction=signal_data.get("bias_direction"),
                bias_level=float(signal_data["bias_level"]) if signal_data.get("bias_level") else None,
                bias_flip_direction=signal_data.get("bias_flip_direction"),
                bias_flip_level=float(signal_data["bias_flip_level"]) if signal_data.get("bias_flip_level") else None,
                entry_timeframe=signal_data.get("entry_timeframe", DEFAULT_ENTRY_TIMEFRAME),
                status=SignalStatus.WATCHING.value,
                last_update=datetime.utcnow()
            )
            
            # Calculate stop level if not provided
            if not signal.stop_level and signal.bias_level:
                # Use bias level as stop by default
                signal.stop_level = signal.bias_level
            
            # If symbol not in active signals, add it
            if signal.symbol not in self.active_signals:
                self.active_signals[signal.symbol] = []
            
            # Add signal to active signals
            self.active_signals[signal.symbol].append(signal)
            
            logger.info(f"Added signal {signal.id} for {signal.symbol} to candle detector")
            
            # Publish signal added event
            self._publish_signal_event(signal, "signal_added")
            
            return signal
    
    def remove_signal(self, signal_id: int) -> bool:
        """
        Remove a signal from the candle detector.
        
        Args:
            signal_id: Signal ID
            
        Returns:
            Success status
        """
        with self.lock:
            for symbol in self.active_signals:
                for i, signal in enumerate(self.active_signals[symbol]):
                    if signal.id == signal_id:
                        # Remove the signal
                        removed_signal = self.active_signals[symbol].pop(i)
                        
                        # If no more signals for this symbol, remove it
                        if not self.active_signals[symbol]:
                            del self.active_signals[symbol]
                        
                        logger.info(f"Removed signal {signal_id} for {removed_signal.symbol} from candle detector")
                        
                        # Publish signal removed event
                        self._publish_signal_event(removed_signal, "signal_removed")
                        
                        return True
            
            logger.warning(f"Signal {signal_id} not found")
            return False
    
    def update_signal_status(self, signal_id: int, status: str, additional_data: Dict[str, Any] = None) -> bool:
        """
        Update the status of a signal.
        
        Args:
            signal_id: Signal ID
            status: New status
            additional_data: Additional data to update
            
        Returns:
            Success status
        """
        with self.lock:
            for symbol in self.active_signals:
                for signal in self.active_signals[symbol]:
                    if signal.id == signal_id:
                        old_status = signal.status
                        signal.status = status
                        signal.last_update = datetime.utcnow()
                        
                        # Update additional data if provided
                        if additional_data:
                            for key, value in additional_data.items():
                                if hasattr(signal, key):
                                    setattr(signal, key, value)
                        
                        logger.info(f"Updated signal {signal_id} status from {old_status} to {status}")
                        
                        # Publish signal status update event
                        self._publish_signal_event(signal, "signal_status_updated")
                        
                        return True
            
            logger.warning(f"Signal {signal_id} not found")
            return False
    
    def get_signal(self, signal_id: int) -> Optional[Signal]:
        """
        Get a signal by ID.
        
        Args:
            signal_id: Signal ID
            
        Returns:
            Signal object or None if not found
        """
        for symbol in self.active_signals:
            for signal in self.active_signals[symbol]:
                if signal.id == signal_id:
                    return signal
        
        return None
    
    def get_active_signals(self, symbol: str = None) -> List[Signal]:
        """
        Get active signals.
        
        Args:
            symbol: Symbol to filter by
            
        Returns:
            List of active signals
        """
        if symbol:
            return self.active_signals.get(symbol, [])
        
        # Return all signals
        signals = []
        for symbol in self.active_signals:
            signals.extend(self.active_signals[symbol])
        
        return signals
    
    def _handle_candle_update(self, message: str):
        """
        Handle candle update from Redis.
        
        Args:
            message: JSON message with candle data
        """
        try:
            # Parse the message
            data = json.loads(message)
            symbol = data["symbol"]
            timeframe = data["timeframe"]
            candle_data = data["candles"]
            
            # If no active signals for this symbol, ignore
            if symbol not in self.active_signals:
                return
            
            logger.debug(f"Received candle update for {symbol} ({timeframe})")
            
            # Update candle cache
            cache_key = f"{symbol}-{timeframe}"
            if cache_key not in self.candle_cache:
                self.candle_cache[cache_key] = []
            
            # Convert candle data to Candle objects
            candles = []
            for raw_candle in candle_data:
                candle = Candle(
                    timestamp=datetime.fromisoformat(raw_candle["timestamp"]),
                    open=float(raw_candle["open"]),
                    high=float(raw_candle["high"]),
                    low=float(raw_candle["low"]),
                    close=float(raw_candle["close"]),
                    volume=float(raw_candle["volume"])
                )
                candles.append(candle)
            
            # Add candles to cache, ensuring they're sorted by timestamp
            self.candle_cache[cache_key].extend(candles)
            self.candle_cache[cache_key].sort(key=lambda x: x.timestamp)
            
            # Limit cache size
            max_candles = 100
            if len(self.candle_cache[cache_key]) > max_candles:
                self.candle_cache[cache_key] = self.candle_cache[cache_key][-max_candles:]
            
            # Process candles for signals with this timeframe
            for signal in self.active_signals[symbol]:
                if signal.entry_timeframe == timeframe:
                    self._process_signal_with_candles(signal, candles)
        
        except Exception as e:
            logger.error(f"Error handling candle update: {e}")
    
    def _process_signal_with_candles(self, signal: Signal, candles: List[Candle]):
        """
        Process a signal with new candles.
        
        Args:
            signal: Signal to process
            candles: New candles to process
        """
        try:
            # Sort candles by timestamp to ensure we process them in order
            candles.sort(key=lambda x: x.timestamp)
            
            for candle in candles:
                # Skip processing if signal is not in a watching or triggered state
                if signal.status not in [SignalStatus.WATCHING.value, SignalStatus.TRIGGERED.value]:
                    continue
                
                # Check if the price has hit the trigger level
                trigger_hit = self._check_trigger_hit(signal, candle)
                
                if signal.status == SignalStatus.WATCHING.value and trigger_hit:
                    # Mark signal as triggered
                    signal.status = SignalStatus.TRIGGERED.value
                    signal.last_update = datetime.utcnow()
                    logger.info(f"Signal {signal.id} for {signal.symbol} triggered at {candle.timestamp}")
                    
                    # Publish signal triggered event
                    self._publish_signal_event(signal, "signal_triggered")
                
                elif signal.status == SignalStatus.TRIGGERED.value:
                    # Check if the candle close confirms the trigger
                    if CANDLE_CONFIRMATION_REQUIRED:
                        confirmation = self._check_trigger_confirmation(signal, candle)
                        
                        if confirmation:
                            # Mark signal as confirmed with this candle
                            signal.status = SignalStatus.CONFIRMED.value
                            signal.confirmation_candle = candle
                            signal.entry_level = candle.close
                            signal.last_update = datetime.utcnow()
                            
                            logger.info(f"Signal {signal.id} for {signal.symbol} confirmed at {candle.timestamp}")
                            
                            # Publish signal confirmed event
                            self._publish_signal_event(signal, "signal_confirmed")
                    else:
                        # No candle confirmation required, mark as confirmed immediately
                        signal.status = SignalStatus.CONFIRMED.value
                        signal.confirmation_candle = candle
                        signal.entry_level = candle.close
                        signal.last_update = datetime.utcnow()
                        
                        logger.info(f"Signal {signal.id} for {signal.symbol} auto-confirmed at {candle.timestamp}")
                        
                        # Publish signal confirmed event
                        self._publish_signal_event(signal, "signal_confirmed")
        
        except Exception as e:
            logger.error(f"Error processing signal {signal.id} with candles: {e}")
    
    def _check_trigger_hit(self, signal: Signal, candle: Candle) -> bool:
        """
        Check if a candle hits the trigger level.
        
        Args:
            signal: Signal to check
            candle: Candle to check
            
        Returns:
            True if trigger hit, False otherwise
        """
        # Get the trigger level
        trigger_level = signal.trigger_value
        
        # Check based on signal category and comparison
        if signal.category == SignalCategoryEnum.BREAKOUT.value:
            # Breakout is a bullish signal, check if price breaks above trigger
            return candle.high > trigger_level
        
        elif signal.category == SignalCategoryEnum.BREAKDOWN.value:
            # Breakdown is a bearish signal, check if price breaks below trigger
            return candle.low < trigger_level
        
        elif signal.category == SignalCategoryEnum.REJECTION.value:
            # Rejection can be bullish or bearish
            if signal.comparison == ComparisonTypeEnum.ABOVE.value:
                # Bearish rejection above level
                return candle.high > trigger_level
            else:
                # Bullish rejection below level
                return candle.low < trigger_level
        
        elif signal.category == SignalCategoryEnum.BOUNCE.value:
            # Bounce can be bullish or bearish
            if signal.comparison == ComparisonTypeEnum.ABOVE.value:
                # Bullish bounce above level
                return candle.low < trigger_level
            else:
                # Bearish bounce below level
                return candle.high > trigger_level
        
        return False
    
    def _check_trigger_confirmation(self, signal: Signal, candle: Candle) -> bool:
        """
        Check if a candle confirms the trigger (full candle close confirmation).
        
        Args:
            signal: Signal to check
            candle: Candle to check
            
        Returns:
            True if confirmed, False otherwise
        """
        # Get the trigger level
        trigger_level = signal.trigger_value
        
        # Check based on signal category and comparison
        if signal.category == SignalCategoryEnum.BREAKOUT.value:
            # Breakout is a bullish signal, check if candle closes above trigger
            return candle.close > trigger_level
        
        elif signal.category == SignalCategoryEnum.BREAKDOWN.value:
            # Breakdown is a bearish signal, check if candle closes below trigger
            return candle.close < trigger_level
        
        elif signal.category == SignalCategoryEnum.REJECTION.value:
            # Rejection can be bullish or bearish
            if signal.comparison == ComparisonTypeEnum.ABOVE.value:
                # Bearish rejection above level
                return candle.close < trigger_level
            else:
                # Bullish rejection below level
                return candle.close > trigger_level
        
        elif signal.category == SignalCategoryEnum.BOUNCE.value:
            # Bounce can be bullish or bearish
            if signal.comparison == ComparisonTypeEnum.ABOVE.value:
                # Bullish bounce above level
                return candle.close > trigger_level
            else:
                # Bearish bounce below level
                return candle.close < trigger_level
        
        return False
    
    def _calculate_moving_average(self, candles: List[Candle], period: int = FAST_MA_PERIOD) -> Optional[float]:
        """
        Calculate a moving average from candles.
        
        Args:
            candles: List of candles
            period: MA period
            
        Returns:
            Moving average value or None if not enough candles
        """
        if len(candles) < period:
            return None
        
        # Get the most recent candles for the period
        recent_candles = candles[-period:]
        
        # Calculate the average close
        avg_close = sum(c.close for c in recent_candles) / period
        
        return avg_close
    
    def _check_volume_spike(self, candles: List[Candle], current_candle: Candle) -> bool:
        """
        Check if the current candle has a volume spike.
        
        Args:
            candles: List of historical candles
            current_candle: Current candle to check
            
        Returns:
            True if volume spike detected, False otherwise
        """
        if len(candles) < 10:
            return False
        
        # Get the previous 10 candles
        previous_candles = candles[-10:-1]
        
        # Calculate average volume
        avg_volume = sum(c.volume for c in previous_candles) / len(previous_candles)
        
        # Check if current volume is a spike (e.g., 50% higher than average)
        return current_candle.volume > (avg_volume * VOLUME_SPIKE_THRESHOLD)
    
    def _check_bias_pivot(self, signal: Signal, current_price: float) -> Optional[str]:
        """
        Check if the current price crosses a bias pivot level.
        
        Args:
            signal: Signal to check
            current_price: Current price to check
            
        Returns:
            New bias direction or None if no change
        """
        if not signal.bias_flip_level:
            return None
        
        # Add a small buffer to avoid flip-flopping around the level
        buffer = signal.bias_flip_level * BIAS_PIVOT_BUFFER
        
        # Check if price crossed the bias flip level
        if signal.bias_direction == BiasDirectionEnum.BULLISH.value:
            # If bullish, check if price dropped below the flip level
            if current_price < (signal.bias_flip_level - buffer):
                return BiasDirectionEnum.BEARISH.value
        
        elif signal.bias_direction == BiasDirectionEnum.BEARISH.value:
            # If bearish, check if price rose above the flip level
            if current_price > (signal.bias_flip_level + buffer):
                return BiasDirectionEnum.BULLISH.value
        
        return None
    
    def _publish_signal_event(self, signal: Signal, event_type: str):
        """
        Publish a signal event to Redis.
        
        Args:
            signal: Signal object
            event_type: Event type
        """
        if not redis_client or not redis_client.available:
            return
        
        # Create event data
        event = {
            "signal_id": signal.id,
            "symbol": signal.symbol,
            "category": signal.category,
            "comparison": signal.comparison,
            "trigger_value": signal.trigger_value,
            "targets": signal.targets,
            "bias_direction": signal.bias_direction,
            "bias_level": signal.bias_level,
            "status": signal.status,
            "entry_level": signal.entry_level,
            "stop_level": signal.stop_level,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add confirmation candle data if available
        if signal.confirmation_candle:
            event["confirmation_candle"] = {
                "timestamp": signal.confirmation_candle.timestamp.isoformat(),
                "open": signal.confirmation_candle.open,
                "high": signal.confirmation_candle.high,
                "low": signal.confirmation_candle.low,
                "close": signal.confirmation_candle.close,
                "volume": signal.confirmation_candle.volume
            }
        
        # Publish to global strategy channel
        redis_client.publish(STRATEGY_CHANNEL, json.dumps(event))
        
        # Publish to ticker-specific channel
        redis_client.publish(f"ticker.{signal.symbol}.signals", json.dumps(event))


# Singleton instance
_candle_detector = None


def get_candle_detector() -> CandleDetector:
    """
    Get the candle detector instance.
    
    Returns:
        Candle detector instance
    """
    global _candle_detector
    
    if _candle_detector is None:
        _candle_detector = CandleDetector()
    
    return _candle_detector


def start_candle_detector():
    """Start the candle detector."""
    detector = get_candle_detector()
    detector.start()


def stop_candle_detector():
    """Stop the candle detector."""
    detector = get_candle_detector()
    detector.stop()