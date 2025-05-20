"""
Alpaca API Client Module

This module provides a simplified interface to the Alpaca Trading API,
abstracting the details of API authentication and request handling.
"""
import os
import logging
import time
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta, timezone

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, OrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')
ALPACA_PAPER = os.environ.get('ALPACA_PAPER', 'true').lower() == 'true'

# Initialize clients
trading_client = None
stock_data_client = None
crypto_data_client = None

def _get_trading_client() -> Optional[TradingClient]:
    """
    Get or initialize the trading client.
    
    Returns:
        TradingClient instance or None if initialization fails
    """
    global trading_client
    
    if trading_client is not None:
        return trading_client
        
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return None
        
    try:
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=ALPACA_PAPER)
        logger.info("Alpaca trading client initialized successfully")
        return trading_client
    except Exception as e:
        logger.error(f"Error initializing Alpaca trading client: {e}")
        return None

def _get_stock_data_client() -> Optional[StockHistoricalDataClient]:
    """
    Get or initialize the stock data client.
    
    Returns:
        StockHistoricalDataClient instance or None if initialization fails
    """
    global stock_data_client
    
    if stock_data_client is not None:
        return stock_data_client
        
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return None
        
    try:
        stock_data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        logger.info("Alpaca stock data client initialized successfully")
        return stock_data_client
    except Exception as e:
        logger.error(f"Error initializing Alpaca stock data client: {e}")
        return None

def get_account_info() -> Optional[Dict]:
    """
    Get account information from Alpaca.
    
    Returns:
        Dict containing account information or None if error
    """
    client = _get_trading_client()
    if not client:
        return None
        
    try:
        account = client.get_account()
        # Convert account object to dictionary
        account_dict = {
            'id': account.id,
            'account_number': account.account_number,
            'status': account.status,
            'currency': account.currency,
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'equity': float(account.equity),
            'position_value': float(account.position_market_value),
            'pattern_day_trader': account.pattern_day_trader,
            'trading_blocked': account.trading_blocked,
            'account_blocked': account.account_blocked,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'equity_change': float(account.portfolio_value) - float(account.last_equity) if account.last_equity else 0.0
        }
        return account_dict
    except Exception as e:
        logger.error(f"Error getting account information: {e}")
        return None

def get_positions() -> Optional[List[Dict]]:
    """
    Get current positions from Alpaca.
    
    Returns:
        List of position dictionaries or None if error
    """
    client = _get_trading_client()
    if not client:
        return None
        
    try:
        positions = client.get_all_positions()
        position_list = []
        
        for position in positions:
            position_dict = {
                'symbol': position.symbol,
                'qty': float(position.qty),
                'side': 'long' if float(position.qty) > 0 else 'short',
                'entry_price': float(position.avg_entry_price),
                'market_value': float(position.market_value),
                'cost_basis': float(position.cost_basis),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc),
                'current_price': float(position.current_price),
                'change_today': float(position.change_today),
                'asset_id': position.asset_id,
                'asset_class': position.asset_class
            }
            position_list.append(position_dict)
            
        return position_list
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return None

def get_orders(status: str = 'open') -> Optional[List[Dict]]:
    """
    Get orders from Alpaca.
    
    Args:
        status: Order status ('open', 'closed', 'all')
        
    Returns:
        List of order dictionaries or None if error
    """
    client = _get_trading_client()
    if not client:
        return None
        
    try:
        # Convert status to boolean parameters for Alpaca API
        if status == 'open':
            orders = client.get_orders(status='open')
        elif status == 'closed':
            orders = client.get_orders(status='closed')
        else:  # 'all'
            orders = client.get_orders(status='all')
        
        order_list = []
        for order in orders:
            order_dict = {
                'id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'side': order.side.name if hasattr(order.side, 'name') else order.side,
                'type': order.type.name if hasattr(order.type, 'name') else order.type,
                'qty': float(order.qty),
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'stop_price': float(order.stop_price) if order.stop_price else None,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
                'filled_at': order.filled_at.isoformat() if order.filled_at else None,
                'expired_at': order.expired_at.isoformat() if order.expired_at else None,
                'canceled_at': order.canceled_at.isoformat() if order.canceled_at else None,
            }
            order_list.append(order_dict)
            
        return order_list
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return None

def get_open_orders() -> Optional[List[Dict]]:
    """
    Get open orders from Alpaca.
    
    Returns:
        List of open order dictionaries or None if error
    """
    return get_orders('open')

def submit_market_order(
    symbol: str,
    quantity: int,
    side: str,
    client_order_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Submit a market order to Alpaca.
    
    Args:
        symbol: Symbol to trade
        quantity: Number of shares/contracts
        side: Trade direction ('buy' or 'sell')
        client_order_id: Optional client-generated order ID
        
    Returns:
        Order details if successful, None otherwise
    """
    client = _get_trading_client()
    if not client:
        return None
        
    try:
        # Map string side to enum
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        
        # Generate client order ID if not provided
        if not client_order_id:
            client_order_id = f"market_{symbol}_{int(time.time())}"
            
        # Create order request
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=order_side,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id
        )
        
        # Submit order
        order = client.submit_order(order_request)
        
        # Convert order object to dictionary
        order_dict = {
            'id': order.id,
            'client_order_id': order.client_order_id,
            'symbol': order.symbol,
            'side': order.side.name,
            'type': order.type.name,
            'qty': float(order.qty),
            'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
            'status': order.status,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        }
        
        return order_dict
    except Exception as e:
        logger.error(f"Error submitting market order: {e}")
        return None

def submit_limit_order(
    symbol: str,
    quantity: int,
    side: str,
    limit_price: float,
    time_in_force: str = 'day',
    client_order_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Submit a limit order to Alpaca.
    
    Args:
        symbol: Symbol to trade
        quantity: Number of shares/contracts
        side: Trade direction ('buy' or 'sell')
        limit_price: Maximum price for buy, minimum for sell
        time_in_force: Order duration ('day', 'gtc', 'ioc', 'fok')
        client_order_id: Optional client-generated order ID
        
    Returns:
        Order details if successful, None otherwise
    """
    client = _get_trading_client()
    if not client:
        return None
        
    try:
        # Map string side to enum
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        
        # Map string time in force to enum
        if time_in_force.lower() == 'day':
            tif = TimeInForce.DAY
        elif time_in_force.lower() == 'gtc':
            tif = TimeInForce.GTC
        elif time_in_force.lower() == 'ioc':
            tif = TimeInForce.IOC
        elif time_in_force.lower() == 'fok':
            tif = TimeInForce.FOK
        else:
            tif = TimeInForce.DAY
            
        # Generate client order ID if not provided
        if not client_order_id:
            client_order_id = f"limit_{symbol}_{int(time.time())}"
            
        # Create order request
        order_request = LimitOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=order_side,
            time_in_force=tif,
            limit_price=limit_price,
            client_order_id=client_order_id
        )
        
        # Submit order
        order = client.submit_order(order_request)
        
        # Convert order object to dictionary
        order_dict = {
            'id': order.id,
            'client_order_id': order.client_order_id,
            'symbol': order.symbol,
            'side': order.side.name,
            'type': order.type.name,
            'limit_price': float(order.limit_price) if order.limit_price else None,
            'qty': float(order.qty),
            'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
            'status': order.status,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        }
        
        return order_dict
    except Exception as e:
        logger.error(f"Error submitting limit order: {e}")
        return None

def cancel_order(order_id: str) -> bool:
    """
    Cancel an order by ID.
    
    Args:
        order_id: Order ID to cancel
        
    Returns:
        True if successful, False otherwise
    """
    client = _get_trading_client()
    if not client:
        return False
        
    try:
        client.cancel_order_by_id(order_id)
        return True
    except Exception as e:
        logger.error(f"Error canceling order {order_id}: {e}")
        return False

def get_latest_quote(symbol: str) -> Optional[Dict]:
    """
    Get the latest quote for a symbol.
    
    Args:
        symbol: Symbol to get quote for
        
    Returns:
        Quote data if successful, None otherwise
    """
    client = _get_stock_data_client()
    if not client:
        return None
        
    try:
        # Get latest quote
        quotes = client.get_latest_quote(symbol)
        if not quotes or symbol not in quotes:
            return None
            
        quote = quotes[symbol]
        
        # Convert quote object to dictionary
        quote_dict = {
            'symbol': symbol,
            'bid_price': float(quote.bid_price) if quote.bid_price else None,
            'bid_size': int(quote.bid_size) if quote.bid_size else 0,
            'ask_price': float(quote.ask_price) if quote.ask_price else None,
            'ask_size': int(quote.ask_size) if quote.ask_size else 0,
            'timestamp': quote.timestamp.isoformat() if quote.timestamp else None,
        }
        
        # Calculate mid price
        if quote_dict['bid_price'] and quote_dict['ask_price']:
            quote_dict['mid_price'] = (quote_dict['bid_price'] + quote_dict['ask_price']) / 2
        else:
            quote_dict['mid_price'] = None
            
        return quote_dict
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        return None