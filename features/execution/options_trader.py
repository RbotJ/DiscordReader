"""
Options Trader Module

This module provides functionality for executing options trades with Alpaca,
including selecting appropriate contracts, managing positions, and implementing
tiered exit strategies.
"""
import logging
import math
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType

from common.constants import OptionType, TradeDirection, SignalState
from common.redis_utils import get_redis_client, publish_event
from features.alpaca.options import get_options_fetcher, OptionsChainFetcher

logger = logging.getLogger(__name__)

# Initialize API credentials from environment variables
API_KEY = os.environ.get("ALPACA_API_KEY")
API_SECRET = os.environ.get("ALPACA_API_SECRET")

trading_client = None
options_fetcher = None

if API_KEY and API_SECRET:
    try:
        trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
        options_fetcher = get_options_fetcher()
        logger.info("Options trader initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing options trader: {e}")


class OptionsTrader:
    """
    Class to manage options trading strategies and execution.
    """
    def __init__(
        self, 
        api_key: str = API_KEY, 
        api_secret: str = API_SECRET, 
        paper: bool = True
    ):
        """
        Initialize the options trader.
        
        Args:
            api_key: Alpaca API key (default: from environment)
            api_secret: Alpaca API secret (default: from environment)
            paper: Whether to use paper trading (default: True)
        """
        if not api_key or not api_secret:
            raise ValueError("Alpaca API credentials required")
            
        self.trading_client = trading_client or TradingClient(api_key, api_secret, paper=paper)
        self.options_fetcher = options_fetcher or get_options_fetcher()
        self.redis = get_redis_client()
        
        # Default risk parameters
        self.max_position_size = 1  # Default to 1 contract per trade
        self.max_drawdown_risk = 500  # Maximum risk per trade in dollars
        
    def execute_signal_trade(self, signal: Dict) -> Optional[Dict]:
        """
        Execute a trade based on a trading signal.
        
        Args:
            signal: Trading signal dictionary
            
        Returns:
            Order information or None if execution failed
        """
        try:
            ticker = signal.get('ticker')
            if not ticker:
                logger.error("Signal missing ticker symbol")
                return None
                
            direction = signal.get('direction', '').lower()
            if direction not in ('long', 'short'):
                logger.error(f"Invalid trade direction: {direction}")
                return None
                
            # Determine option type based on direction
            option_type = OptionType.CALL if direction == 'long' else OptionType.PUT
            
            # Find suitable option contract
            contract = self._select_contract(ticker, option_type, signal)
            if not contract:
                logger.error(f"Could not find suitable {option_type.value} option for {ticker}")
                return None
                
            # Calculate position size
            qty = self._calculate_position_size(contract, signal)
            if qty <= 0:
                logger.error(f"Invalid position size: {qty}")
                return None
                
            # Execute the trade
            order = self._submit_option_order(contract, qty, OrderSide.BUY)
            if not order:
                logger.error("Failed to submit option order")
                return None
                
            # Set up exit orders if needed
            self._setup_exit_strategy(contract, signal, order)
            
            return order
            
        except Exception as e:
            logger.error(f"Error executing signal trade: {e}")
            return None
            
    def _select_contract(
        self, 
        ticker: str, 
        option_type: OptionType, 
        signal: Dict
    ) -> Optional[Dict]:
        """
        Select the appropriate options contract based on the trading signal.
        
        Args:
            ticker: Underlying stock symbol
            option_type: CALL or PUT
            signal: Trading signal with trigger and target information
            
        Returns:
            Selected option contract or None if not found
        """
        # Check if the fetcher is available
        if not self.options_fetcher:
            logger.error("Options fetcher not available")
            return None
            
        # Try to find same-day expiration contracts
        expiration = self.options_fetcher.get_same_day_expiration(ticker)
        if not expiration:
            logger.error(f"No suitable expiration found for {ticker}")
            return None
            
        # Target delta for ATM options
        target_delta = 0.50
            
        # Find contract with delta closest to target
        contract = self.options_fetcher.find_atm_options(
            symbol=ticker,
            option_type=option_type,
            target_delta=target_delta,
            expiration=expiration
        )
        
        return contract
        
    def _calculate_position_size(self, contract: Dict, signal: Dict) -> int:
        """
        Calculate the appropriate position size based on risk parameters.
        
        Args:
            contract: Option contract information
            signal: Trading signal with risk parameters
            
        Returns:
            Number of contracts to trade
        """
        # Get contract price (use midpoint of bid/ask)
        bid = float(contract.get('bid', 0) or 0)
        ask = float(contract.get('ask', 0) or 0)
        
        if ask <= 0:
            logger.error(f"Invalid ask price: {ask}")
            return 0
            
        # Use midpoint if bid is available, otherwise use ask
        contract_price = (bid + ask) / 2 if bid > 0 else ask
        
        # Calculate max risk per contract (assume 100% loss)
        risk_per_contract = contract_price * 100  # Options contracts are for 100 shares
        
        # Calculate position size based on max drawdown risk
        max_size_by_risk = math.floor(self.max_drawdown_risk / risk_per_contract)
        
        # Apply maximum position size constraint
        position_size = min(max_size_by_risk, self.max_position_size)
        
        # Ensure at least 1 contract
        return max(1, position_size)
        
    def _submit_option_order(
        self, 
        contract: Dict, 
        qty: int, 
        side: OrderSide
    ) -> Optional[Dict]:
        """
        Submit an options order.
        
        Args:
            contract: Option contract to trade
            qty: Number of contracts
            side: BUY or SELL
            
        Returns:
            Order information or None if execution failed
        """
        try:
            symbol = contract.get('symbol')
            if not symbol:
                logger.error("Contract missing symbol")
                return None
                
            # Create market order request
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit the order
            order = self.trading_client.submit_order(order_request)
            
            # Format the response
            formatted_order = {
                'id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'option_symbol': symbol,
                'side': side.value,
                'qty': qty,
                'type': 'market',
                'status': order.status.value,
                'created_at': str(order.created_at) if hasattr(order, 'created_at') else None,
                'filled_at': str(order.filled_at) if hasattr(order, 'filled_at') else None,
                'filled_price': order.filled_avg_price if hasattr(order, 'filled_avg_price') else None,
            }
            
            logger.info(f"Submitted {side.value} order for {qty} {symbol}: {formatted_order['id']}")
            return formatted_order
            
        except Exception as e:
            logger.error(f"Error submitting option order: {e}")
            return None
            
    def _setup_exit_strategy(
        self, 
        contract: Dict, 
        signal: Dict, 
        entry_order: Dict
    ) -> bool:
        """
        Set up tiered exit strategy with target orders.
        
        Args:
            contract: Option contract information
            signal: Trading signal with target information
            entry_order: Entry order information
            
        Returns:
            Success status
        """
        # Get targets from signal
        targets = signal.get('targets', [])
        if not targets:
            logger.warning("No targets specified in signal, skipping exit strategy")
            return False
            
        try:
            # Track exit orders
            exit_orders = []
            entry_qty = int(entry_order.get('qty', 0))
            
            # Process each target
            remaining_qty = entry_qty
            for target in targets:
                # Get target price and percentage allocation
                price_target = target.get('price')
                percentage = target.get('percentage', 0)
                
                if not price_target or percentage <= 0:
                    continue
                    
                # Calculate quantity for this target
                target_qty = max(1, round(entry_qty * percentage))
                
                # Adjust for remaining quantity
                if target_qty > remaining_qty:
                    target_qty = remaining_qty
                    
                remaining_qty -= target_qty
                
                if target_qty <= 0:
                    continue
                    
                # We'll implement limit orders for these targets later
                # For now, just log the plan
                logger.info(f"Exit plan: Sell {target_qty} contracts at price target {price_target}")
                
                # TODO: Create and track limit orders for exits
                
            return True
            
        except Exception as e:
            logger.error(f"Error setting up exit strategy: {e}")
            return False
            
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Success status
        """
        try:
            self.trading_client.cancel_order(order_id)
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
            
    def close_position(self, symbol: str) -> Optional[Dict]:
        """
        Close an existing position.
        
        Args:
            symbol: Symbol of the position to close
            
        Returns:
            Order information or None if execution failed
        """
        try:
            # Get current position
            position = self.trading_client.get_position(symbol)
            
            # Determine side for closing
            side = OrderSide.SELL if position.side == 'long' else OrderSide.BUY
            
            # Create market order to close
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=position.qty,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit the order
            order = self.trading_client.submit_order(order_request)
            
            logger.info(f"Closed position for {symbol}: {order.id}")
            
            # Format the response
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': side.value,
                'status': order.status.value
            }
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return None


def get_options_trader() -> Optional[OptionsTrader]:
    """
    Get an options trader instance.
    
    Returns:
        OptionsTrader instance or None if not available
    """
    if not API_KEY or not API_SECRET:
        logger.error("Alpaca API credentials not set in environment")
        return None
        
    try:
        return OptionsTrader(API_KEY, API_SECRET)
    except Exception as e:
        logger.error(f"Error creating options trader: {e}")
        return None


def init_options_trader() -> bool:
    """
    Initialize the options trader component.
    
    Returns:
        Success status
    """
    try:
        trader = get_options_trader()
        if not trader:
            logger.error("Failed to initialize options trader")
            return False
            
        logger.info("Options trader initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing options trader: {e}")
        return False