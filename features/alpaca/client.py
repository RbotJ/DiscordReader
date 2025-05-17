"""
Alpaca Client Module

This module provides the client interface for connecting to Alpaca API
for paper trading and market data.
"""
import os
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date, timedelta

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockQuotesRequest, StockBarsRequest, StockLatestQuoteRequest
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.common.exceptions import APIError

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

# Global clients
trading_client = None
data_client = None

def initialize_clients() -> bool:
    """Initialize Alpaca clients if credentials are available."""
    global trading_client, data_client

    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return False

    try:
        # Initialize trading client for paper trading
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True)

        # Initialize data client
        data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)

        logger.info("Alpaca clients initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Alpaca clients: {e}")
        return False

def get_account_info() -> Dict:
    """
    Get account information from Alpaca.

    Returns:
        Dict containing account information
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return {}

    try:
        account = trading_client.get_account()
        return account._raw
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return {}

def get_positions() -> List[Dict]:
    """
    Get current positions from Alpaca.

    Returns:
        List of position dictionaries
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return []

    try:
        positions = trading_client.get_all_positions()
        return [p._raw for p in positions]
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []

def get_open_orders() -> List[Dict]:
    """
    Get open orders from Alpaca.

    Returns:
        List of order dictionaries
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return []

    try:
        orders = trading_client.get_all_orders(status=QueryOrderStatus.OPEN)
        return [o._raw for o in orders]
    except Exception as e:
        logger.error(f"Error getting open orders: {e}")
        return []

def get_latest_quote(symbol: str) -> Optional[Dict]:
    """
    Get the latest quote for a symbol.

    Args:
        symbol: Ticker symbol

    Returns:
        Quote dictionary if successful, None otherwise
    """
    if not data_client:
        logger.warning("Data client not initialized")
        return None

    try:
        req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        resp = data_client.get_stock_latest_quote(req)
        return resp[symbol]._raw
    except Exception as e:
        logger.error(f"Error getting latest quote for {symbol}: {e}")
        return None

def submit_market_order(symbol: str, qty: int, side: str) -> Optional[Dict]:
    """
    Submit a market order to Alpaca using typed request objects.
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return None

    try:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        order = trading_client.submit_order(market_order_request=req)
        return order._raw

    except Exception as e:
        logger.error(f"Error submitting market order: {e}")
        return None

def submit_limit_order(
    symbol: str,
    qty: int,
    side: str,
    limit_price: float,
    time_in_force: str = 'day',
    client_order_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Submit a limit order to Alpaca.
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return None

    try:
        # Map string side to enum
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL

        # Map string time_in_force to enum
        order_tif = TimeInForce.DAY
        if time_in_force.lower() == 'gtc':
            order_tif = TimeInForce.GTC
        elif time_in_force.lower() == 'ioc':
            order_tif = TimeInForce.IOC
        elif time_in_force.lower() == 'fok':
            order_tif = TimeInForce.FOK

        # Create limit order request
        order_data = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=order_tif,
            limit_price=limit_price,
            client_order_id=client_order_id
        )

        # Submit order
        order = trading_client.submit_order(order_data)
        return order._raw

    except Exception as e:
        logger.error(f"Error submitting limit order: {e}")
        return None

def cancel_order(order_id: str) -> bool:
    """
    Cancel an order by ID.
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return False

    try:
        trading_client.cancel_order_by_id(order_id)
        logger.info(f"Order cancelled: {order_id}")
        return True
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return False

def calculate_position_size(symbol: str, risk_amount: float = 500.0) -> int:
    """
    Calculate position size based on live option premiums and risk parameters.

    Args:
        symbol: Option symbol
        risk_amount: Maximum risk amount per position in dollars

    Returns:
        int: Number of contracts to trade
    """
    try:
        # Get account information and buying power
        account = trading_client.get_account()._raw
        buying_power = float(account["buying_power"])

        # Check if we have enough buying power for minimum risk
        if buying_power < risk_amount:
            logger.warning(f"Insufficient buying power (${buying_power}) for minimum risk (${risk_amount})")
            return 0

        # Fetch latest option quote
        quote = data_client.get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=symbol)
        )[symbol]._raw

        # Get ask price for conservative sizing
        ask_price = float(quote["ask_price"])
        if ask_price <= 0:
            logger.warning(f"Invalid ask price (${ask_price}) for {symbol}")
            return 1

        # Calculate maximum contracts based on risk amount
        # One contract controls 100 shares
        max_contracts = int(risk_amount / (ask_price * 100))
        position_size = max(1, max_contracts)

        logger.info(f"Calculated position size for {symbol}: {position_size} contracts at ${ask_price}/share")
        return position_size

    except Exception as e:
        logger.error(f"Error calculating position size for {symbol}: {e}")
        return 1  # Default to 1 contract on error

# Initialize clients on module import
initialize_clients()