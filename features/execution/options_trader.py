"""
Options Trader Module

This module handles the execution of options trades based on signals,
including placing orders, managing positions, and handling stop-loss/take-profit.
"""
import logging
import time
import threading
from typing import Dict, List, Optional, Tuple, Union

from features.alpaca.client import (
    get_trading_client, 
    get_account_info, 
    get_positions,
    submit_market_order,
    submit_limit_order,
    submit_bracket_order
)
from features.alpaca.options_enums import OptionSide
from features.options.selector import select_best_option_contract

# Configure logger
logger = logging.getLogger(__name__)

# Global state
_trader_running = False
_trader_thread = None
_active_signals = {}  # Tracks active signals by symbol

def execute_signal_trade(
    symbol: str,
    signal_type: str,
    price_target: float,
    risk_amount: float = 500.0
) -> Optional[Dict]:
    """
    Execute a trade based on a signal.
    
    Args:
        symbol: The underlying ticker symbol
        signal_type: Type of signal (breakout, breakdown, rejection, bounce)
        price_target: Target price for the signal
        risk_amount: Maximum risk amount in dollars
        
    Returns:
        Order information or None if trade could not be executed
    """
    try:
        # Select the appropriate options contract
        contract = select_best_option_contract(
            symbol=symbol,
            signal_type=signal_type,
            price_target=price_target,
            risk_amount=risk_amount
        )
        
        if not contract:
            logger.warning(f"No suitable contract found for {symbol} {signal_type} signal")
            return None
            
        # Determine order side (always buy for now, as we select calls or puts based on signal)
        order_side = "buy"
        
        # Calculate stop and target prices
        current_price = contract.get('mid', contract.get('ask'))
        if not current_price:
            logger.warning(f"No price available for contract {contract['symbol']}")
            return None
            
        # Standard 10% take profit, 10% stop loss
        take_profit_price = current_price * 1.10
        stop_loss_price = current_price * 0.90
        
        # Place a bracket order
        try:
            order_result = submit_bracket_order(
                symbol=contract['symbol'],
                qty=contract['quantity'],
                side=order_side,
                time_in_force='day',
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price
            )
            
            if order_result:
                logger.info(f"Successfully placed bracket order for {contract['symbol']}")
                
                # Track the active signal
                _active_signals[symbol] = {
                    'signal_type': signal_type,
                    'contract': contract,
                    'order_id': order_result.get('id'),
                    'entry_price': current_price,
                    'take_profit': take_profit_price,
                    'stop_loss': stop_loss_price,
                    'status': 'open',
                    'timestamp': time.time()
                }
                
                return order_result
            else:
                logger.error(f"Failed to place bracket order for {contract['symbol']}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing bracket order for {contract['symbol']}: {e}")
            
            # Try with just a market order if bracket order fails
            try:
                order_result = submit_market_order(
                    symbol=contract['symbol'],
                    qty=contract['quantity'],
                    side=order_side,
                    time_in_force='day'
                )
                
                if order_result:
                    logger.info(f"Successfully placed market order for {contract['symbol']}")
                    
                    # Track the active signal
                    _active_signals[symbol] = {
                        'signal_type': signal_type,
                        'contract': contract,
                        'order_id': order_result.get('id'),
                        'entry_price': current_price,
                        'take_profit': take_profit_price,
                        'stop_loss': stop_loss_price,
                        'status': 'open',
                        'timestamp': time.time()
                    }
                    
                    return order_result
                else:
                    logger.error(f"Failed to place market order for {contract['symbol']}")
                    return None
            except Exception as e2:
                logger.error(f"Error placing market order for {contract['symbol']}: {e2}")
                return None
                
    except Exception as e:
        logger.error(f"Error executing signal trade for {symbol}: {e}")
        return None

def manage_position(symbol: str, current_price: float) -> Optional[Dict]:
    """
    Manage an open position based on current price.
    Checks for take-profit or stop-loss conditions.
    
    Args:
        symbol: The underlying ticker symbol
        current_price: Current price of the position
        
    Returns:
        Position status information
    """
    if symbol not in _active_signals:
        return None
        
    position_info = _active_signals[symbol]
    if position_info['status'] != 'open':
        return position_info
        
    # Check if we've hit take-profit or stop-loss
    if current_price >= position_info['take_profit']:
        # Take profit
        logger.info(f"Take profit triggered for {symbol} at {current_price}")
        
        # Update status
        position_info['status'] = 'closed_profit'
        position_info['exit_price'] = current_price
        position_info['profit_pct'] = (current_price - position_info['entry_price']) / position_info['entry_price'] * 100
        
        return position_info
        
    elif current_price <= position_info['stop_loss']:
        # Stop loss
        logger.info(f"Stop loss triggered for {symbol} at {current_price}")
        
        # Update status
        position_info['status'] = 'closed_loss'
        position_info['exit_price'] = current_price
        position_info['profit_pct'] = (current_price - position_info['entry_price']) / position_info['entry_price'] * 100
        
        return position_info
        
    return position_info

def get_active_positions() -> Dict:
    """
    Get information on all active positions.
    
    Returns:
        Dictionary of active positions by symbol
    """
    return {k: v for k, v in _active_signals.items() if v['status'] == 'open'}

def get_closed_positions() -> Dict:
    """
    Get information on all closed positions.
    
    Returns:
        Dictionary of closed positions by symbol
    """
    return {k: v for k, v in _active_signals.items() if v['status'] != 'open'}

def init_options_trader() -> bool:
    """
    Initialize the options trader.
    
    Returns:
        Success status
    """
    try:
        # Check if we can connect to Alpaca
        client = get_trading_client()
        if not client:
            logger.warning("Trading client not initialized")
            return False
            
        # Start position monitor thread
        global _trader_thread, _trader_running
        
        if _trader_thread and _trader_thread.is_alive():
            logger.info("Options trader already running")
            return True
            
        _trader_running = True
        _trader_thread = threading.Thread(
            target=_position_monitor_thread,
            daemon=True,
            name="OptionsTraderThread"
        )
        _trader_thread.start()
        
        logger.info("Options trader initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing options trader: {e}")
        return False

def shutdown_options_trader() -> bool:
    """
    Shutdown the options trader.
    
    Returns:
        Success status
    """
    global _trader_running, _trader_thread
    
    try:
        if not _trader_thread or not _trader_thread.is_alive():
            logger.info("Options trader not running")
            return True
            
        _trader_running = False
        _trader_thread.join(timeout=5.0)
        
        if _trader_thread.is_alive():
            logger.warning("Options trader thread did not stop gracefully")
            return False
        else:
            logger.info("Options trader shut down successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error shutting down options trader: {e}")
        return False

def _position_monitor_thread() -> None:
    """
    Thread function to monitor positions.
    """
    global _trader_running
    
    logger.info("Position monitor thread started")
    
    try:
        while _trader_running:
            try:
                # Get all open positions from Alpaca
                positions = get_positions()
                
                # Check for exits (missed take-profits or stop-losses)
                for symbol, position_info in list(_active_signals.items()):
                    if position_info['status'] != 'open':
                        continue
                        
                    # Check if position is still in Alpaca
                    contract_symbol = position_info['contract']['symbol']
                    position_exists = any(p.get('symbol') == contract_symbol for p in positions)
                    
                    if not position_exists:
                        # Position was closed
                        logger.info(f"Position for {symbol} was closed")
                        
                        # Try to get latest price
                        current_price = None
                        # Set status based on time (if recent, assume profit)
                        position_info['status'] = 'closed_unknown'
                        position_info['exit_price'] = current_price
                        
                # Refresh position prices
                # (In a production system, we would subscribe to real-time quotes)
                
                # Sleep for a bit to avoid API rate limits
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in position monitor thread: {e}")
                time.sleep(30)
                
    except Exception as e:
        logger.error(f"Fatal error in position monitor thread: {e}")
    finally:
        _trader_running = False
        logger.info("Position monitor thread stopped")