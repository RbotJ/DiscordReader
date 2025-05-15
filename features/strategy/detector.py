import logging
import threading
import time
from typing import Dict, Set, List
from datetime import datetime

from common.models import TickerSetup, Signal
from common.utils import publish_event
from features.setups.parser import get_active_setups
from features.market.price_feed import subscribe_symbol, get_last_price

# Configure logging
logger = logging.getLogger(__name__)

# Global state
_running = False
_active_signals: Dict[str, List[TickerSetup]] = {}
_triggered_signals: Set[int] = set()  # Store IDs of triggered signals

def start_signal_detector() -> bool:
    """Start the signal detector in a background thread"""
    global _running
    
    if _running:
        logger.info("Signal detector already running")
        return True
    
    try:
        # Start in a new thread
        thread = threading.Thread(target=_run_signal_detector, daemon=True)
        thread.start()
        
        _running = True
        logger.info("Signal detector started")
        return True
    except Exception as e:
        logger.error(f"Failed to start signal detector: {str(e)}")
        return False

def _run_signal_detector() -> None:
    """Run the signal detector loop"""
    global _active_signals, _triggered_signals
    
    while True:
        try:
            # Get all active setups
            active_setups = get_active_setups()
            
            # Reset active signals
            _active_signals = {}
            
            # Process each setup
            for setup in active_setups:
                symbol = setup.symbol
                
                # Skip if already triggered
                setup_id = id(setup)
                if setup_id in _triggered_signals:
                    continue
                
                # Add to active signals for this symbol
                if symbol not in _active_signals:
                    _active_signals[symbol] = []
                
                _active_signals[symbol].append(setup)
                
                # Subscribe to price updates for this symbol
                subscribe_symbol(symbol, _on_price_update)
            
            # Log active signals
            logger.info(f"Monitoring {len(_active_signals)} symbols for signals")
            
            # Sleep for 5 minutes before refreshing active setups
            time.sleep(300)
            
        except Exception as e:
            logger.error(f"Error in signal detector loop: {str(e)}")
            time.sleep(60)  # Sleep on error and try again

def _on_price_update(symbol: str, price: float) -> None:
    """Handle price update for a symbol"""
    global _active_signals, _triggered_signals
    
    # Skip if no active signals for this symbol
    if symbol not in _active_signals:
        return
    
    # Check each setup for triggers
    for setup in _active_signals[symbol]:
        # Skip if already triggered
        setup_id = id(setup)
        if setup_id in _triggered_signals:
            continue
        
        # Check if triggered
        if setup.is_triggered(price):
            logger.info(f"Signal triggered for {symbol} at {price}")
            
            # Mark as triggered
            _triggered_signals.add(setup_id)
            
            # Publish trigger event
            publish_event("strategy.signal_triggered", {
                "symbol": symbol,
                "price": price,
                "setup_id": setup_id,
                "signals": [signal.dict() for signal in setup.signals],
                "bias": setup.bias.dict() if setup.bias else None,
                "timestamp": datetime.now().isoformat()
            })

def get_active_signals() -> Dict[str, List[TickerSetup]]:
    """Get all active signals being monitored"""
    return _active_signals.copy()

def add_manual_trigger(symbol: str, price: float, signal_type: str) -> bool:
    """Manually trigger a signal"""
    try:
        # Create a simple signal event
        publish_event("strategy.signal_triggered", {
            "symbol": symbol,
            "price": price,
            "manual": True,
            "signal_type": signal_type,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Manual signal triggered for {symbol} at {price} ({signal_type})")
        return True
    except Exception as e:
        logger.error(f"Error triggering manual signal: {str(e)}")
        return False

def reset_triggered_signal(setup_id: int) -> bool:
    """Reset a triggered signal to allow it to trigger again"""
    global _triggered_signals
    
    try:
        if setup_id in _triggered_signals:
            _triggered_signals.remove(setup_id)
            logger.info(f"Reset triggered signal: {setup_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error resetting triggered signal: {str(e)}")
        return False
