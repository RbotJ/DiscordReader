"""
Position Management Module

This module provides functions for managing Alpaca positions,
including end-of-day position cleanup and position sizing.
"""
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .client import get_positions, submit_market_order, get_account_info, get_trading_client

# Configure logger
logger = logging.getLogger(__name__)

# Cleanup thread reference
_cleanup_thread = None
_thread_running = False

def close_all_positions() -> bool:
    """
    Close all open positions using Alpaca's close_position method.
    
    Returns:
        bool: Success status
    """
    try:
        # Get all current positions
        positions = get_positions()
        
        if not positions:
            logger.info("No positions to close")
            return True
        
        logger.info(f"Closing {len(positions)} position(s)")
        success = True
        
        try:
            logger.info("Closing all positions")
            trading_client = get_trading_client()
            if trading_client:
                trading_client.close_all_positions(cancel_orders=True)
                logger.info("Successfully closed all positions")
                return True
            else:
                logger.error("Trading client not initialized")
                return False
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            return False
        
        return success
    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        return False

def _cleanup_thread_func() -> None:
    """Thread function for end-of-day position cleanup using Alpaca market clock."""
    global _thread_running
    
    logger.info("Position cleanup thread started")
    _thread_running = True
    
    try:
        while _thread_running:
            try:
                from .client import trading_client
                
                # Get current market clock from Alpaca
                clock = trading_client.get_clock()
                
                # If market is open and within 5 minutes of close
                if clock.is_open and (clock.next_close - clock.timestamp).total_seconds() < 300:
                    logger.info("Market close approaching, closing all positions")
                    close_all_positions()
                    
                    # Sleep until after market close to avoid multiple cleanups
                    time.sleep(300)  # Sleep for 5 minutes
                
                # Check every minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error checking market clock: {e}")
                time.sleep(60)  # Still sleep on error to avoid tight loops
                
    except Exception as e:
        logger.error(f"Error in position cleanup thread: {e}")
    finally:
        _thread_running = False
        logger.info("Position cleanup thread stopped")

def calculate_position_size(symbol: str, risk_amount: float = 500.0) -> int:
    """
    Calculate position size based on risk parameters.
    
    Args:
        symbol: Ticker symbol
        risk_amount: Maximum risk amount per position in dollars
        
    Returns:
        int: Number of contracts/shares to trade
    """
    try:
        # Get account information
        account = get_account_info()
        
        # Default to 1 contract if we can't calculate
        if not account:
            logger.warning(f"Could not get account info, defaulting to 1 contract for {symbol}")
            return 1
        
        # Get buying power
        buying_power = float(account.get('buying_power', 0))
        
        # Use $500 maximum risk per position as default
        # We'll implement more sophisticated sizing later
        
        # For options, default to 1 contract if account can afford it
        # (Assuming ~$500-1000 per contract for simplicity)
        if buying_power >= 1000:
            return 1
        else:
            logger.warning(f"Insufficient buying power (${buying_power}) for {symbol}, defaulting to 1 contract")
            return 1
    except Exception as e:
        logger.error(f"Error calculating position size for {symbol}: {e}")
        return 1

def schedule_eod_cleanup() -> bool:
    """
    Schedule end-of-day position cleanup.
    
    Returns:
        bool: Success status
    """
    global _cleanup_thread, _thread_running
    
    try:
        # Check if thread is already running
        if _cleanup_thread and _cleanup_thread.is_alive():
            logger.info("Position cleanup thread already running")
            return True
        
        # Start new thread for position cleanup
        _cleanup_thread = threading.Thread(
            target=_cleanup_thread_func,
            daemon=True,
            name="PositionCleanupThread"
        )
        _cleanup_thread.start()
        
        # Wait a moment to ensure thread starts
        time.sleep(0.1)
        
        if _cleanup_thread.is_alive():
            logger.info("Position cleanup thread started successfully")
            return True
        else:
            logger.error("Position cleanup thread failed to start")
            return False
    except Exception as e:
        logger.error(f"Error scheduling end-of-day position cleanup: {e}")
        return False

def stop_eod_cleanup() -> bool:
    """
    Stop end-of-day position cleanup.
    
    Returns:
        bool: Success status
    """
    global _thread_running, _cleanup_thread
    
    try:
        if not _cleanup_thread or not _cleanup_thread.is_alive():
            logger.info("Position cleanup thread not running")
            return True
        
        # Signal thread to stop
        _thread_running = False
        
        # Wait for thread to stop (with timeout)
        _cleanup_thread.join(timeout=5.0)
        
        if _cleanup_thread.is_alive():
            logger.warning("Position cleanup thread did not stop gracefully")
            return False
        else:
            logger.info("Position cleanup thread stopped successfully")
            return True
    except Exception as e:
        logger.error(f"Error stopping end-of-day position cleanup: {e}")
        return False