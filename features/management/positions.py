import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import alpaca_trade_api as tradeapi

from common.models import Position
from common.utils import publish_event, load_config

# Configure logging
logger = logging.getLogger(__name__)

# In-memory position tracking
_positions: List[Position] = []
_position_history: List[Position] = []

def start_position_manager() -> bool:
    """Start the position manager in a background thread"""
    try:
        # Start in a new thread
        thread = threading.Thread(target=_run_position_manager, daemon=True)
        thread.start()
        
        logger.info("Position manager started")
        return True
    except Exception as e:
        logger.error(f"Failed to start position manager: {str(e)}")
        return False

def _run_position_manager() -> None:
    """Run the position manager loop"""
    while True:
        try:
            # Update positions
            update_positions()
            
            # Sleep for 60 seconds
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in position manager loop: {str(e)}")
            time.sleep(60)  # Sleep on error and try again

def update_positions() -> bool:
    """
    Update positions from Alpaca API
    
    Returns:
        True if update was successful
    """
    global _positions
    
    try:
        # Load config
        config = load_config()
        
        # Initialize Alpaca API
        api = tradeapi.REST(
            key_id=config['alpaca']['api_key'],
            secret_key=config['alpaca']['api_secret'],
            base_url=config['alpaca']['base_url'],
            api_version='v2'
        )
        
        # Get current positions
        try:
            alpaca_positions = api.list_positions()
            
            # Convert to our Position model
            current_positions = []
            
            for pos in alpaca_positions:
                # Extract symbol from option symbol if needed
                symbol = pos.symbol
                option_symbol = None
                
                if "O:" in symbol:
                    # This is an option position
                    option_symbol = symbol
                    symbol = symbol.split("O:")[1].split()[0]
                
                position = Position(
                    symbol=symbol,
                    quantity=float(pos.qty),
                    side="buy" if float(pos.qty) > 0 else "sell",
                    average_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price),
                    unrealized_pl=float(pos.unrealized_pl),
                    realized_pl=float(pos.unrealized_plpc) * float(pos.avg_entry_price) * abs(float(pos.qty)),
                    entry_time=datetime.fromisoformat(pos.created_at.replace('Z', '+00:00')),
                    option_symbol=option_symbol
                )
                
                current_positions.append(position)
            
            # Check for closed positions (in previous _positions but not current)
            current_symbols = {p.symbol + (p.option_symbol or '') for p in current_positions}
            
            for old_pos in _positions:
                pos_key = old_pos.symbol + (old_pos.option_symbol or '')
                
                if pos_key not in current_symbols:
                    # Position was closed
                    old_pos.exit_time = datetime.now()
                    old_pos.exit_reason = "unknown"  # We don't know from just polling
                    
                    # Add to history
                    _position_history.append(old_pos)
                    
                    # Publish position closed event
                    publish_event("position.closed", {
                        "symbol": old_pos.symbol,
                        "option_symbol": old_pos.option_symbol,
                        "quantity": old_pos.quantity,
                        "pl": old_pos.realized_pl,
                        "pl_percent": old_pos.pl_percent,
                        "duration_days": old_pos.duration
                    })
            
            # Update positions
            _positions = current_positions
            
            logger.info(f"Updated positions: {len(_positions)} active positions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to get positions from Alpaca: {str(e)}")
            
            # For testing/development, use cached positions
            if "API_KEY" not in config['alpaca'] or not config['alpaca']['api_key']:
                logger.warning("Using cached positions (DEVELOPMENT ONLY)")
                return True
            else:
                # Real API error
                raise e
    
    except Exception as e:
        logger.error(f"Error updating positions: {str(e)}")
        return False

def add_position(
    symbol: str,
    quantity: float,
    side: str,
    average_price: float,
    current_price: float,
    option_symbol: Optional[str] = None,
    strategy: Optional[str] = None
) -> bool:
    """
    Add a new position (for manual entry or simulation)
    
    Args:
        symbol: Underlying symbol
        quantity: Position quantity
        side: 'buy' or 'sell'
        average_price: Average entry price
        current_price: Current price
        option_symbol: Optional option symbol
        strategy: Optional strategy name
    
    Returns:
        True if the position was added successfully
    """
    global _positions
    
    try:
        # Create position
        position = Position(
            symbol=symbol,
            quantity=quantity,
            side=side,
            average_price=average_price,
            current_price=current_price,
            unrealized_pl=(current_price - average_price) * quantity if side == "buy" else (average_price - current_price) * quantity,
            realized_pl=0,
            entry_time=datetime.now(),
            option_symbol=option_symbol,
            strategy=strategy
        )
        
        # Add to positions
        _positions.append(position)
        
        # Publish position added event
        publish_event("position.opened", {
            "symbol": symbol,
            "option_symbol": option_symbol,
            "quantity": quantity,
            "side": side,
            "average_price": average_price,
            "strategy": strategy
        })
        
        logger.info(f"Added position: {symbol} {quantity} @ {average_price}")
        return True
    
    except Exception as e:
        logger.error(f"Error adding position: {str(e)}")
        return False

def close_position(
    symbol: str,
    exit_price: float,
    exit_reason: str,
    option_symbol: Optional[str] = None
) -> bool:
    """
    Close a position (for manual exit or simulation)
    
    Args:
        symbol: Symbol to close
        exit_price: Exit price
        exit_reason: Reason for exit
        option_symbol: Optional option symbol
    
    Returns:
        True if the position was closed successfully
    """
    global _positions, _position_history
    
    try:
        # Find the position
        position_index = None
        
        for i, pos in enumerate(_positions):
            if pos.symbol == symbol:
                if option_symbol and pos.option_symbol == option_symbol:
                    position_index = i
                    break
                elif not option_symbol and not pos.option_symbol:
                    position_index = i
                    break
        
        if position_index is None:
            logger.error(f"Position not found: {symbol} {option_symbol or ''}")
            return False
        
        # Get the position
        position = _positions[position_index]
        
        # Calculate realized P/L
        if position.side == "buy":
            position.realized_pl = (exit_price - position.average_price) * abs(position.quantity)
        else:
            position.realized_pl = (position.average_price - exit_price) * abs(position.quantity)
        
        # Set exit details
        position.exit_time = datetime.now()
        position.exit_reason = exit_reason
        position.current_price = exit_price
        
        # Add to history
        _position_history.append(position)
        
        # Remove from active positions
        _positions.pop(position_index)
        
        # Publish position closed event
        publish_event("position.closed", {
            "symbol": symbol,
            "option_symbol": option_symbol,
            "quantity": position.quantity,
            "pl": position.realized_pl,
            "pl_percent": position.pl_percent,
            "duration_days": position.duration,
            "exit_reason": exit_reason
        })
        
        logger.info(f"Closed position: {symbol} @ {exit_price} ({exit_reason})")
        return True
    
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        return False

def get_positions() -> List[Position]:
    """
    Get all active positions
    
    Returns:
        List of Position objects
    """
    return _positions.copy()

def get_position_history() -> List[Position]:
    """
    Get all historical positions
    
    Returns:
        List of closed Position objects
    """
    return _position_history.copy()

def get_position(
    symbol: str, 
    option_symbol: Optional[str] = None
) -> Optional[Position]:
    """
    Get a specific position
    
    Args:
        symbol: Symbol to find
        option_symbol: Optional option symbol
    
    Returns:
        Position object or None if not found
    """
    for pos in _positions:
        if pos.symbol == symbol:
            if option_symbol and pos.option_symbol == option_symbol:
                return pos
            elif not option_symbol and not pos.option_symbol:
                return pos
    
    return None
