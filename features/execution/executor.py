"""
Order Execution Module

This module provides functionality for executing trades through Alpaca's API,
including order placement, management, and monitoring.
"""
import os
import logging
import time
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from features.alpaca.client import (
    submit_market_order, submit_limit_order, cancel_order,
    get_orders, get_open_orders, get_account_info
)
from common.events import publish_event

# Configure logger
logger = logging.getLogger(__name__)

class OrderExecutor:
    """
    Service for executing and managing trading orders.
    """
    
    def __init__(self):
        """Initialize the order executor."""
        self.db_events = True  # Flag to indicate we're using DB events instead of Redis
        self.pending_orders = {}  # Track orders in progress
        self.filled_orders = {}   # Track orders that have been filled
        
    def execute_market_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        order_properties: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Execute a market order.
        
        Args:
            symbol: Symbol to trade
            quantity: Number of shares/contracts
            side: Trade direction ('buy' or 'sell')
            order_properties: Additional order properties
            
        Returns:
            Order details if successful, None otherwise
        """
        try:
            # Validate parameters
            if not symbol or quantity <= 0 or side not in ['buy', 'sell']:
                logger.error(f"Invalid order parameters: {symbol}, {quantity}, {side}")
                return None
                
            # Log the order attempt
            logger.info(f"Executing market {side} order for {quantity} {symbol}")
            
            # Execute the order
            order = submit_market_order(symbol, quantity, side)
            
            if not order:
                logger.error(f"Failed to submit market order for {symbol}")
                return None
                
            # Store order properties if provided
            if order_properties and order.get('id'):
                order_id = order['id']
                self.pending_orders[order_id] = {
                    'order': order,
                    'properties': order_properties,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Publish order event to database events system
                if self.db_events:
                    try:
                        event = {
                            'event_type': 'order_created',
                            'order_id': order_id,
                            'symbol': symbol,
                            'side': side,
                            'quantity': quantity,
                            'order_type': 'market',
                            'properties': order_properties
                        }
                        publish_event('events:orders', event)
                    except Exception as e:
                        logger.warning(f"Error publishing order event to database: {e}")
                
            return order
        except Exception as e:
            logger.error(f"Error executing market order: {e}", exc_info=True)
            return None
            
    def execute_limit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        limit_price: float,
        time_in_force: str = 'day',
        order_properties: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Execute a limit order.
        
        Args:
            symbol: Symbol to trade
            quantity: Number of shares/contracts
            side: Trade direction ('buy' or 'sell')
            limit_price: Maximum price for buy, minimum for sell
            time_in_force: Order duration ('day', 'gtc', 'ioc', 'fok')
            order_properties: Additional order properties
            
        Returns:
            Order details if successful, None otherwise
        """
        try:
            # Validate parameters
            if not symbol or quantity <= 0 or side not in ['buy', 'sell'] or limit_price <= 0:
                logger.error(f"Invalid order parameters: {symbol}, {quantity}, {side}, {limit_price}")
                return None
                
            # Log the order attempt
            logger.info(f"Executing limit {side} order for {quantity} {symbol} @ {limit_price}")
            
            # Generate client order ID (optional)
            client_order_id = f"algotrader_{int(time.time())}"
            
            # Execute the order
            order = submit_limit_order(
                symbol, quantity, side, limit_price, time_in_force, client_order_id
            )
            
            if not order:
                logger.error(f"Failed to submit limit order for {symbol}")
                return None
                
            # Store order properties if provided
            if order_properties and order.get('id'):
                order_id = order['id']
                self.pending_orders[order_id] = {
                    'order': order,
                    'properties': order_properties,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Publish order event to Redis
                if self.redis:
                    try:
                        event = {
                            'event': 'order_created',
                            'order_id': order_id,
                            'symbol': symbol,
                            'side': side,
                            'quantity': quantity,
                            'order_type': 'limit',
                            'limit_price': limit_price,
                            'time_in_force': time_in_force,
                            'properties': order_properties
                        }
                        self.redis.publish('events:orders', json.dumps(event))
                    except Exception as e:
                        logger.warning(f"Error publishing order event to Redis: {e}")
                
            return order
        except Exception as e:
            logger.error(f"Error executing limit order: {e}", exc_info=True)
            return None
            
    def execute_bracket_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        entry_price: Optional[float] = None,  # If None, use market order
        take_profit_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        order_properties: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Execute a bracket order (entry with take profit and stop loss).
        
        This is a higher-level function that uses the basic order functions
        to implement a common trading pattern.
        
        Args:
            symbol: Symbol to trade
            quantity: Number of shares/contracts
            side: Trade direction ('buy' or 'sell')
            entry_price: Entry price (optional, market order if None)
            take_profit_price: Take profit price (optional)
            stop_loss_price: Stop loss price (optional)
            order_properties: Additional order properties
            
        Returns:
            Dictionary with entry order details if successful, None otherwise
        """
        try:
            # Validate parameters
            if not symbol or quantity <= 0 or side not in ['buy', 'sell']:
                logger.error(f"Invalid bracket order parameters: {symbol}, {quantity}, {side}")
                return None
                
            # Check prices for consistency
            if side == 'buy':
                if take_profit_price and take_profit_price <= entry_price:
                    logger.warning(f"Take profit price ({take_profit_price}) should be higher than entry price ({entry_price}) for buy orders")
                if stop_loss_price and stop_loss_price >= entry_price:
                    logger.warning(f"Stop loss price ({stop_loss_price}) should be lower than entry price ({entry_price}) for buy orders")
            else:  # sell
                if take_profit_price and take_profit_price >= entry_price:
                    logger.warning(f"Take profit price ({take_profit_price}) should be lower than entry price ({entry_price}) for sell orders")
                if stop_loss_price and stop_loss_price <= entry_price:
                    logger.warning(f"Stop loss price ({stop_loss_price}) should be higher than entry price ({entry_price}) for sell orders")
                    
            # Start by placing the entry order
            entry_order = None
            if entry_price:
                entry_order = self.execute_limit_order(
                    symbol, quantity, side, entry_price, 'day', order_properties
                )
            else:
                entry_order = self.execute_market_order(
                    symbol, quantity, side, order_properties
                )
                
            if not entry_order:
                logger.error(f"Failed to submit entry order for {symbol}")
                return None
                
            # For now, we'll manually track the bracket components
            # In a production system, we'd use Alpaca's bracket order API
            entry_order_id = entry_order.get('id')
            if entry_order_id:
                # Store bracket order details
                bracket_details = {
                    'entry_order_id': entry_order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side,
                    'entry_price': entry_price,
                    'take_profit_price': take_profit_price,
                    'stop_loss_price': stop_loss_price,
                    'take_profit_order_id': None,
                    'stop_loss_order_id': None,
                    'properties': order_properties,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Publish bracket order event to Redis
                if self.redis:
                    try:
                        event = {
                            'event': 'bracket_order_created',
                            'bracket_details': bracket_details
                        }
                        self.redis.publish('events:orders', json.dumps(event))
                    except Exception as e:
                        logger.warning(f"Error publishing bracket order event to Redis: {e}")
                
            return entry_order
        except Exception as e:
            logger.error(f"Error executing bracket order: {e}", exc_info=True)
            return None
            
    def execute_option_order(
        self,
        option_symbol: str,
        quantity: int,
        side: str,
        price_type: str = 'market',  # 'market' or 'limit'
        limit_price: Optional[float] = None,
        order_properties: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Execute an option order.
        
        Args:
            option_symbol: Option symbol (OCC format)
            quantity: Number of contracts
            side: Trade direction ('buy' or 'sell')
            price_type: 'market' or 'limit'
            limit_price: Price for limit orders
            order_properties: Additional order properties
            
        Returns:
            Order details if successful, None otherwise
        """
        try:
            # Validate parameters
            if not option_symbol or quantity <= 0 or side not in ['buy', 'sell']:
                logger.error(f"Invalid option order parameters: {option_symbol}, {quantity}, {side}")
                return None
                
            if price_type == 'limit' and (not limit_price or limit_price <= 0):
                logger.error(f"Invalid limit price for option order: {limit_price}")
                return None
                
            # Log the order attempt
            if price_type == 'market':
                logger.info(f"Executing market {side} order for {quantity} {option_symbol} options")
                return self.execute_market_order(option_symbol, quantity, side, order_properties)
            else:
                logger.info(f"Executing limit {side} order for {quantity} {option_symbol} options @ {limit_price}")
                return self.execute_limit_order(
                    option_symbol, quantity, side, limit_price, 'day', order_properties
                )
        except Exception as e:
            logger.error(f"Error executing option order: {e}", exc_info=True)
            return None
    
    def cancel_pending_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if canceled successfully, False otherwise
        """
        try:
            result = cancel_order(order_id)
            
            if result:
                # Remove from pending orders
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]
                    
                # Publish order canceled event to Redis
                if self.redis:
                    try:
                        event = {
                            'event': 'order_canceled',
                            'order_id': order_id
                        }
                        self.redis.publish('events:orders', json.dumps(event))
                    except Exception as e:
                        logger.warning(f"Error publishing order canceled event to Redis: {e}")
                
            return result
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False
            
    def get_position_risk(self, account_value: float, position_cost: float) -> float:
        """
        Calculate position risk as a percentage of account value.
        
        Args:
            account_value: Total account value
            position_cost: Cost of the position
            
        Returns:
            Risk percentage (0-100)
        """
        if account_value <= 0:
            return 100.0  # Maximum risk if account value is invalid
            
        return (position_cost / account_value) * 100.0
        
    def check_position_risk(
        self,
        symbol: str,
        quantity: int,
        price: float,
        max_risk_percent: float = 5.0
    ) -> bool:
        """
        Check if a position's risk is within acceptable limits.
        
        Args:
            symbol: Symbol to trade
            quantity: Number of shares/contracts
            price: Price per share/contract
            max_risk_percent: Maximum risk as percentage of account value
            
        Returns:
            True if risk is acceptable, False otherwise
        """
        try:
            # Get account information
            account = get_account_info()
            
            if not account:
                logger.warning("Could not get account information")
                return False
                
            # Get account value
            account_value = float(account.get('equity', 0))
            
            if account_value <= 0:
                logger.warning(f"Invalid account value: {account_value}")
                return False
                
            # Calculate position cost
            # For options, each contract is for 100 shares
            multiplier = 100 if 'C' in symbol or 'P' in symbol else 1
            position_cost = quantity * price * multiplier
            
            # Calculate risk
            risk_percent = self.get_position_risk(account_value, position_cost)
            
            # Check if risk is acceptable
            if risk_percent > max_risk_percent:
                logger.warning(f"Position risk ({risk_percent:.2f}%) exceeds maximum ({max_risk_percent}%)")
                return False
                
            logger.info(f"Position risk ({risk_percent:.2f}%) is within acceptable limits")
            return True
        except Exception as e:
            logger.error(f"Error checking position risk: {e}")
            return False
            
    def update_order_status(self):
        """
        Update the status of pending orders.
        
        This method should be called periodically to update the status
        of pending orders and process filled orders.
        """
        try:
            # Get all orders
            orders = get_orders('all')
            
            if not orders:
                return
                
            # Process each order
            for order in orders:
                order_id = order.get('id')
                if not order_id:
                    continue
                    
                status = order.get('status')
                
                # Check if this order is being tracked
                if order_id in self.pending_orders:
                    # Update the order
                    self.pending_orders[order_id]['order'] = order
                    
                    # Check if filled
                    if status == 'filled':
                        # Move to filled orders
                        self.filled_orders[order_id] = self.pending_orders[order_id]
                        del self.pending_orders[order_id]
                        
                        # Publish order filled event to Redis
                        if self.redis:
                            try:
                                event = {
                                    'event': 'order_filled',
                                    'order_id': order_id,
                                    'order': order,
                                    'properties': self.filled_orders[order_id].get('properties')
                                }
                                self.redis.publish('events:orders', json.dumps(event))
                            except Exception as e:
                                logger.warning(f"Error publishing order filled event to Redis: {e}")
                                
                    # Check if failed/canceled
                    elif status in ['canceled', 'expired', 'rejected', 'suspended']:
                        # Remove from pending orders
                        del self.pending_orders[order_id]
                        
                        # Publish order failed event to database events system
                        if self.db_events:
                            try:
                                event = {
                                    'event_type': 'order_failed',
                                    'order_id': order_id,
                                    'status': status,
                                    'order': order
                                }
                                publish_event('events:orders', event)
                            except Exception as e:
                                logger.warning(f"Error publishing order failed event to database: {e}")
        except Exception as e:
            logger.error(f"Error updating order status: {e}")

# Global instance
order_executor = OrderExecutor()

def get_order_executor() -> OrderExecutor:
    """
    Get the global order executor instance.
    
    Returns:
        OrderExecutor instance
    """
    return order_executor