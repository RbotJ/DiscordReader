import logging
import threading
import time
from datetime import datetime
from typing import Dict, Set, List, Optional

from common.models import TickerSetup, Position
from common.utils import publish_event, subscribe_to_channel
from features.market.price_feed import subscribe_symbol, get_last_price
from features.management.positions import get_positions, close_position

# Configure logging
logger = logging.getLogger(__name__)

# Global state
_running = False
_exit_rules: Dict[str, Dict] = {}  # symbol -> exit rules

def start_exit_monitor() -> bool:
    """Start the exit monitor in a background thread"""
    global _running
    
    if _running:
        logger.info("Exit monitor already running")
        return True
    
    try:
        # Subscribe to signal triggered events
        subscribe_to_channel("strategy.signal_triggered", _on_signal_triggered)
        
        # Start in a new thread
        thread = threading.Thread(target=_run_exit_monitor, daemon=True)
        thread.start()
        
        _running = True
        logger.info("Exit monitor started")
        return True
    except Exception as e:
        logger.error(f"Failed to start exit monitor: {str(e)}")
        return False

def _run_exit_monitor() -> None:
    """Run the exit monitor loop"""
    while True:
        try:
            # Get all positions
            positions = get_positions()
            
            # Check each position against exit rules
            for position in positions:
                symbol = position.symbol
                option_symbol = position.option_symbol
                
                # Subscribe to price updates for this symbol
                subscribe_symbol(symbol, lambda s, p: _check_exit_rules(s, p, symbol))
                
                # Check exit rules now with current price
                current_price = get_last_price(symbol)
                if current_price > 0:
                    _check_exit_rules(symbol, current_price, symbol)
            
            # Sleep for 30 seconds
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in exit monitor loop: {str(e)}")
            time.sleep(60)  # Sleep on error and try again

def _on_signal_triggered(data: Dict) -> None:
    """Handle signal triggered event"""
    try:
        symbol = data.get("symbol")
        
        # Skip if no symbol or no signals
        if not symbol or "signals" not in data:
            return
        
        # Extract target prices from signals
        targets = []
        bias_flip = None
        
        for signal in data.get("signals", []):
            if "targets" in signal:
                targets.extend(signal.get("targets", []))
        
        # Extract bias flip if available
        if "bias" in data and data["bias"] and "flip" in data["bias"] and data["bias"]["flip"]:
            bias_flip = data["bias"]["flip"]
        
        # Store exit rules for this symbol
        _exit_rules[symbol] = {
            "targets": targets,
            "bias_flip": bias_flip,
            "entry_price": data.get("price", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Added exit rules for {symbol}: targets={targets}, bias_flip={bias_flip}")
    
    except Exception as e:
        logger.error(f"Error processing signal triggered event: {str(e)}")

def _check_exit_rules(symbol: str, price: float, context: str) -> None:
    """
    Check if exit rules are triggered for a symbol
    
    Args:
        symbol: Symbol to check
        price: Current price
        context: Context string for logging
    """
    try:
        # Get positions for this symbol
        positions = [p for p in get_positions() if p.symbol == symbol]
        
        # Skip if no positions
        if not positions:
            return
        
        # Get exit rules for this symbol
        if symbol not in _exit_rules:
            return
        
        exit_rules = _exit_rules[symbol]
        
        # Check target prices
        for target in exit_rules.get("targets", []):
            for position in positions:
                if _is_target_hit(position, price, target):
                    # Target hit, exit position
                    logger.info(f"Target hit for {symbol} @ {price} (target: {target})")
                    
                    close_position(
                        symbol=symbol,
                        exit_price=price,
                        exit_reason=f"target_{target}",
                        option_symbol=position.option_symbol
                    )
        
        # Check bias flip
        bias_flip = exit_rules.get("bias_flip")
        if bias_flip:
            flip_condition = bias_flip.get("condition")
            flip_price = bias_flip.get("price", 0)
            
            if flip_condition == "above" and price > flip_price:
                for position in positions:
                    logger.info(f"Bias flipped for {symbol} @ {price} (above {flip_price})")
                    
                    close_position(
                        symbol=symbol,
                        exit_price=price,
                        exit_reason="bias_flip",
                        option_symbol=position.option_symbol
                    )
            
            elif flip_condition == "below" and price < flip_price:
                for position in positions:
                    logger.info(f"Bias flipped for {symbol} @ {price} (below {flip_price})")
                    
                    close_position(
                        symbol=symbol,
                        exit_price=price,
                        exit_reason="bias_flip",
                        option_symbol=position.option_symbol
                    )
    
    except Exception as e:
        logger.error(f"Error checking exit rules for {symbol}: {str(e)}")

def _is_target_hit(position: Position, price: float, target: float) -> bool:
    """
    Check if a target price is hit for a position
    
    Args:
        position: Position to check
        price: Current price
        target: Target price
    
    Returns:
        True if target is hit
    """
    # For long positions, target hit when price rises to target
    if position.side == "buy" and position.average_price < target <= price:
        return True
    
    # For short positions, target hit when price falls to target
    if position.side == "sell" and position.average_price > target >= price:
        return True
    
    return False

def add_manual_exit_rule(
    symbol: str,
    target_price: Optional[float] = None,
    stop_price: Optional[float] = None
) -> bool:
    """
    Add a manual exit rule
    
    Args:
        symbol: Symbol to add rule for
        target_price: Optional target price
        stop_price: Optional stop price
    
    Returns:
        True if rule was added
    """
    try:
        # Get or create exit rules for this symbol
        if symbol not in _exit_rules:
            _exit_rules[symbol] = {
                "targets": [],
                "stops": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # Add target price
        if target_price is not None:
            if "targets" not in _exit_rules[symbol]:
                _exit_rules[symbol]["targets"] = []
            
            _exit_rules[symbol]["targets"].append(target_price)
        
        # Add stop price
        if stop_price is not None:
            if "stops" not in _exit_rules[symbol]:
                _exit_rules[symbol]["stops"] = []
            
            _exit_rules[symbol]["stops"].append(stop_price)
        
        logger.info(f"Added manual exit rule for {symbol}: target={target_price}, stop={stop_price}")
        return True
    
    except Exception as e:
        logger.error(f"Error adding manual exit rule: {str(e)}")
        return False

def get_exit_rules() -> Dict[str, Dict]:
    """
    Get all exit rules
    
    Returns:
        Dictionary of exit rules by symbol
    """
    return _exit_rules.copy()
