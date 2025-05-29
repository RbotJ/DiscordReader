"""
Candle Detector Module

This module implements candle-based signal detection for trading setups.
It monitors candle closes and detects when price crosses trigger levels using
PostgreSQL for event notification instead of Redis.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Set, Any, Optional

from common.event_constants import EventChannels
from common.events import publish_event, subscribe_to_events
from features.market.historical_data import get_historical_data
from common.db import db
from common.db_models import CandleModel

# Configure logger
logger = logging.getLogger(__name__)

# Thread control variables
_detector_thread = None
_thread_running = False
_last_event_id = 0

# Store active trading signals
_active_signals: Dict[str, List[Dict[str, Any]]] = {}

def init_candle_detector() -> bool:
    """
    Initialize the candle detector.

    Returns:
        bool: Success status
    """
    global _detector_thread, _thread_running

    try:
        # Check if detector thread is already running
        if _detector_thread and _detector_thread.is_alive():
            logger.info("Candle detector thread already running")
            return True

        # Start detector thread
        _detector_thread = threading.Thread(
            target=_candle_detector_thread,
            daemon=True,
            name="CandleDetectorThread"
        )
        _thread_running = True
        _detector_thread.start()

        # Wait a moment to ensure thread starts
        time.sleep(0.1)

        if _detector_thread.is_alive():
            logger.info("Candle detector thread started successfully")
            return True
        else:
            logger.error("Candle detector thread failed to start")
            return False
    except Exception as e:
        logger.error(f"Error initializing candle detector: {e}")
        return False

def _candle_detector_thread() -> None:
    """Candle detector thread function."""
    global _thread_running, _last_event_id

    logger.info("Candle detector thread started")

    # Define channel for candle updates
    candle_channel = "candles:all"

    # Get the latest event ID to start polling from
    try:
        from app import app
        with app.app_context():
            _last_event_id = get_latest_event_id()
            logger.info(f"Starting candle detector polling from event ID: {_last_event_id}")
    except Exception as e:
        logger.warning(f"Error getting latest event ID: {e}")
        _last_event_id = 0

    while _thread_running:
        try:
            # Poll for candle update events from PostgreSQL
            from app import app
            with app.app_context():
                events = poll_events([candle_channel], _last_event_id)

                # Process any new events
                for event in events:
                    try:
                        # Update the last event ID
                        _last_event_id = max(_last_event_id, event.get('id', 0))

                        # Get the payload
                        payload = event.get('payload', {})
                        if not payload:
                            continue

                        # Extract candle data
                        symbol = payload.get('ticker')
                        timeframe = payload.get('timeframe')
                        is_closed = payload.get('is_closed', False)

                        # Only process closed candles
                        if not is_closed:
                            continue

                        # Process candle for signal detection
                        _process_candle(symbol, timeframe, payload)
                    except Exception as e:
                        logger.error(f"Error processing candle event: {e}")

            # Sleep briefly to avoid excessive database polling
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in candle detector thread: {e}")
            time.sleep(5)  # Sleep longer on error

    logger.info("Candle detector thread stopped")

def _process_candle(symbol: str, timeframe: str, candle_data: Dict[str, Any]) -> None:
    """
    Process a closed candle for signal detection.

    Args:
        symbol: Ticker symbol
        timeframe: Candle timeframe
        candle_data: Candle data dictionary
    """
    try:
        # Skip if we're not tracking any signals for this symbol
        if symbol not in _active_signals:
            return

        # Get candle values
        close_price = float(candle_data.get('close', 0))
        high_price = float(candle_data.get('high', 0))
        low_price = float(candle_data.get('low', 0))

        # Check each active signal for this symbol
        for signal in _active_signals[symbol]:
            # Get trigger level
            trigger_level = signal.get('trigger', {}).get('price', 0)

            # Skip if no trigger level
            if not trigger_level:
                continue

            # Get signal direction (breakout/breakdown) and state
            category = signal.get('category', '')
            status = signal.get('status', 'pending')

            # Skip if already triggered or completed
            if status in ['triggered', 'completed']:
                continue

            # Check for breakout (price closes above trigger level)
            if category == 'breakout' and close_price > trigger_level:
                # Breakout signal confirmed by candle close
                _update_signal_status(symbol, signal, 'triggered', close_price)

                # Publish signal event
                _publish_signal_event(symbol, signal, 'trigger', close_price)

            # Check for breakdown (price closes below trigger level)
            elif category == 'breakdown' and close_price < trigger_level:
                # Breakdown signal confirmed by candle close
                _update_signal_status(symbol, signal, 'triggered', close_price)

                # Publish signal event
                _publish_signal_event(symbol, signal, 'trigger', close_price)

            # Check target levels for active signals
            if status == 'triggered':
                _check_target_levels(symbol, signal, close_price, high_price, low_price)
    except Exception as e:
        logger.error(f"Error processing candle for {symbol}: {e}")

def _check_target_levels(
    symbol: str, 
    signal: Dict[str, Any], 
    close_price: float, 
    high_price: float, 
    low_price: float
) -> None:
    """
    Check if price has reached any target levels.

    Args:
        symbol: Ticker symbol
        signal: Signal dictionary
        close_price: Current close price
        high_price: Current high price
        low_price: Current low price
    """
    try:
        # Get target levels
        targets = signal.get('targets', [])
        hit_targets = signal.get('hit_targets', [])
        category = signal.get('category', '')

        # Check each target
        for target in targets:
            # Skip if target already hit
            if target in hit_targets:
                continue

            target_price = float(target.get('price', 0))

            # Check for breakout target hit (price reaches target level)
            if category == 'breakout' and high_price >= target_price:
                # Target hit
                hit_targets.append(target)

                # Update signal
                signal['hit_targets'] = hit_targets

                # Publish target hit event
                _publish_signal_event(symbol, signal, 'target_hit', high_price, target)

            # Check for breakdown target hit (price reaches target level)
            elif category == 'breakdown' and low_price <= target_price:
                # Target hit
                hit_targets.append(target)

                # Update signal
                signal['hit_targets'] = hit_targets

                # Publish target hit event
                _publish_signal_event(symbol, signal, 'target_hit', low_price, target)

        # Check if all targets hit
        if len(hit_targets) == len(targets) and targets:
            # All targets hit, signal completed
            _update_signal_status(symbol, signal, 'completed', close_price)

            # Publish signal completed event
            _publish_signal_event(symbol, signal, 'completed', close_price)
    except Exception as e:
        logger.error(f"Error checking target levels for {symbol}: {e}")

def _update_signal_status(symbol: str, signal: Dict[str, Any], status: str, price: float) -> None:
    """
    Update signal status.

    Args:
        symbol: Ticker symbol
        signal: Signal dictionary
        status: New status
        price: Current price
    """
    # Update signal status
    signal['status'] = status
    signal['last_price'] = price
    signal['last_update'] = datetime.now().isoformat()

def _publish_signal_event(
    symbol: str, 
    signal: Dict[str, Any], 
    event_type: str, 
    price: float,
    target: Optional[Dict[str, Any]] = None
) -> None:
    """
    Publish signal event to PostgreSQL event bus.

    Args:
        symbol: Ticker symbol
        signal: Signal dictionary
        event_type: Event type ('trigger', 'target_hit', 'completed')
        price: Current price
        target: Target hit (if event_type is 'target_hit')
    """
    try:
        # Create event data
        event_data = {
            'ticker': symbol,
            'signal_id': signal.get('id'),
            'category': signal.get('category'),
            'event_type': event_type,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }

        # Add target information if provided
        if target and event_type == 'target_hit':
            event_data['target'] = target

        # Use app context for database operations
        from app import app
        with app.app_context():
            # Publish to symbol-specific channel
            publish_event(f"signals:{symbol}", event_type, event_data)

            # Also publish to general signals channel
            publish_event("signals:all", event_type, event_data)

        logger.info(f"Published signal {event_type} event for {symbol}")
    except Exception as e:
        logger.error(f"Error publishing signal event for {symbol}: {e}")

def add_signal(signal_data: Dict[str, Any]) -> bool:
    """
    Add a signal to be monitored.

    Args:
        signal_data: Signal data dictionary

    Returns:
        bool: Success status
    """
    global _active_signals

    try:
        # Extract symbol
        symbol = signal_data.get('ticker')

        if not symbol:
            logger.error("Signal missing ticker symbol")
            return False

        # Initialize signal list for this symbol if needed
        if symbol not in _active_signals:
            _active_signals[symbol] = []

        # Add signal to list
        _active_signals[symbol].append(signal_data)

        # Log signal added
        logger.info(f"Added signal for {symbol}: {signal_data.get('category')}")

        # Publish signal added event
        event_data = {
            'ticker': symbol,
            'signal_id': signal_data.get('id'),
            'category': signal_data.get('category'),
            'event_type': 'added',
            'timestamp': datetime.now().isoformat()
        }

        # Use app context for database operations
        from app import app
        with app.app_context():
            # Publish to PostgreSQL event bus
            publish_event(f"signals:{symbol}", "signal_added", event_data)
            publish_event("signals:all", "signal_added", event_data)

        return True
    except Exception as e:
        logger.error(f"Error adding signal: {e}")
        return False

def get_active_signals(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get active signals.

    Args:
        symbol: Ticker symbol to filter signals (if None, return all signals)

    Returns:
        List of signal dictionaries
    """
    if symbol:
        return _active_signals.get(symbol, [])
    else:
        # Flatten all signals into a single list
        return [signal for signals in _active_signals.values() for signal in signals]

def remove_signal(signal_id: str) -> bool:
    """
    Remove a signal by ID.

    Args:
        signal_id: Signal ID to remove

    Returns:
        bool: Success status
    """
    try:
        # Look for signal in all symbols
        for symbol, signals in _active_signals.items():
            for i, signal in enumerate(signals):
                if str(signal.get('id')) == str(signal_id):
                    # Remove signal from list
                    removed_signal = signals.pop(i)

                    # Log signal removed
                    logger.info(f"Removed signal {signal_id} for {symbol}")

                    # Publish signal removed event
                    event_data = {
                        'ticker': symbol,
                        'signal_id': signal_id,
                        'category': removed_signal.get('category'),
                        'event_type': 'removed',
                        'timestamp': datetime.now().isoformat()
                    }

                    # Use app context for database operations
                    from app import app
                    with app.app_context():
                        # Publish to PostgreSQL event bus
                        publish_event(f"signals:{symbol}", "signal_removed", event_data)
                        publish_event("signals:all", "signal_removed", event_data)

                    return True

        logger.warning(f"Signal {signal_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error removing signal {signal_id}: {e}")
        return False

def shutdown() -> bool:
    """
    Shutdown the candle detector.

    Returns:
        bool: Success status
    """
    global _thread_running, _detector_thread

    try:
        # Signal thread to stop
        _thread_running = False

        # Wait for thread to stop (with timeout)
        if _detector_thread and _detector_thread.is_alive():
            _detector_thread.join(timeout=5.0)

            if _detector_thread.is_alive():
                logger.warning("Candle detector thread did not stop gracefully")
                return False

        logger.info("Candle detector shut down successfully")
        return True
    except Exception as e:
        logger.error(f"Error shutting down candle detector: {e}")
        return False

def detector_running() -> bool:
    """
    Check if the candle detector is currently running.

    Returns:
        bool: True if the detector is running, False otherwise
    """
    global _thread_running, _detector_thread

    return _thread_running and _detector_thread is not None and _detector_thread.is_alive()