"""
Alpaca Client Module

This module provides the client interface for connecting to Alpaca API
for paper trading and market data.
"""
import os
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, date, timedelta

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest, StopOrderRequest,
    StopLimitOrderRequest, GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

# Global clients
trading_client = None
historical_client = None
data_stream = None

def initialize_clients():
    """Initialize Alpaca clients if credentials are available."""
    global trading_client, historical_client, data_stream
    
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return False
    
    try:
        # Initialize trading client for paper trading
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True)
        
        # Initialize historical data client
        historical_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        
        # Initialize real-time data stream
        data_stream = StockDataStream(ALPACA_API_KEY, ALPACA_API_SECRET)
        
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
        return {
            'id': account.id,
            'status': account.status,
            'equity': account.equity,
            'cash': account.cash,
            'buying_power': account.buying_power,
            'position_market_value': account.position_market_value,
            'portfolio_value': account.portfolio_value,
            'trading_blocked': account.trading_blocked,
            'pattern_day_trader': account.pattern_day_trader
        }
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
        return [{
            'symbol': position.symbol,
            'qty': position.qty,
            'market_value': position.market_value,
            'avg_entry_price': position.avg_entry_price,
            'side': position.side,
            'unrealized_pl': position.unrealized_pl,
            'unrealized_plpc': position.unrealized_plpc,
            'current_price': position.current_price
        } for position in positions]
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
        orders = trading_client.get_orders(GetOrdersRequest(status='open'))
        return [{
            'id': order.id,
            'symbol': order.symbol,
            'qty': order.qty,
            'filled_qty': order.filled_qty,
            'side': order.side,
            'type': order.type,
            'time_in_force': order.time_in_force,
            'limit_price': order.limit_price,
            'stop_price': order.stop_price,
            'status': order.status,
            'created_at': order.created_at,
            'updated_at': order.updated_at
        } for order in orders]
    except Exception as e:
        logger.error(f"Error getting open orders: {e}")
        return []

def submit_market_order(
    symbol: str,
    qty: int,
    side: str,
    time_in_force: str = 'day',
    client_order_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Submit a market order to Alpaca.
    
    Args:
        symbol: The ticker symbol
        qty: Quantity of shares
        side: 'buy' or 'sell'
        time_in_force: Time in force (default: 'day')
        client_order_id: Optional client order ID
        
    Returns:
        Order dictionary if successful, None otherwise
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
        
        # Create market order request
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=order_tif,
            client_order_id=client_order_id
        )
        
        # Submit order
        order = trading_client.submit_order(order_data)
        
        logger.info(f"Market order submitted: {order.id} - {symbol} {qty} {side}")
        
        return {
            'id': order.id,
            'client_order_id': order.client_order_id,
            'symbol': order.symbol,
            'qty': order.qty,
            'side': order.side,
            'type': order.type,
            'time_in_force': order.time_in_force,
            'status': order.status,
            'created_at': order.created_at
        }
    except APIError as e:
        logger.error(f"API error submitting market order: {e}")
        return None
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
    
    Args:
        symbol: The ticker symbol
        qty: Quantity of shares
        side: 'buy' or 'sell'
        limit_price: Limit price
        time_in_force: Time in force (default: 'day')
        client_order_id: Optional client order ID
        
    Returns:
        Order dictionary if successful, None otherwise
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
        
        logger.info(f"Limit order submitted: {order.id} - {symbol} {qty} {side} @ {limit_price}")
        
        return {
            'id': order.id,
            'client_order_id': order.client_order_id,
            'symbol': order.symbol,
            'qty': order.qty,
            'side': order.side,
            'type': order.type,
            'limit_price': order.limit_price,
            'time_in_force': order.time_in_force,
            'status': order.status,
            'created_at': order.created_at
        }
    except APIError as e:
        logger.error(f"API error submitting limit order: {e}")
        return None
    except Exception as e:
        logger.error(f"Error submitting limit order: {e}")
        return None

def get_latest_quote(symbol: str) -> Optional[Dict]:
    """
    Get the latest quote for a symbol.
    
    Args:
        symbol: Ticker symbol
        
    Returns:
        Quote dictionary if successful, None otherwise
    """
    if not historical_client:
        logger.warning("Historical client not initialized")
        return None
    
    try:
        # Get latest quote
        request = StockQuotesRequest(
            symbol_or_symbols=[symbol],
            start=datetime.now() - timedelta(minutes=5),
            end=datetime.now()
        )
        quotes = historical_client.get_stock_quotes(request)
        
        if symbol in quotes and len(quotes[symbol]) > 0:
            latest = quotes[symbol][-1]
            return {
                'symbol': symbol,
                'ask_price': latest.ask_price,
                'ask_size': latest.ask_size,
                'bid_price': latest.bid_price,
                'bid_size': latest.bid_size,
                'timestamp': latest.timestamp
            }
        else:
            logger.warning(f"No quote data found for {symbol}")
            return None
    except Exception as e:
        logger.error(f"Error getting latest quote for {symbol}: {e}")
        return None

def get_latest_bars(symbols: List[str], timeframe: str = '1D', limit: int = 10) -> Dict[str, List[Dict]]:
    """
    Get the latest bars for symbols.
    
    Args:
        symbols: List of ticker symbols
        timeframe: Bar timeframe ('1D', '1H', '15Min', etc.)
        limit: Number of bars to retrieve
        
    Returns:
        Dictionary of symbol -> list of bar dictionaries
    """
    if not historical_client:
        logger.warning("Historical client not initialized")
        return {}
    
    try:
        # Map string timeframe to enum
        tf = TimeFrame.DAY
        if timeframe == '1H':
            tf = TimeFrame.HOUR
        elif timeframe == '15Min':
            tf = TimeFrame.MINUTE
            # Adjust for specific minute timeframes if needed
        
        # Get bars
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=tf,
            start=datetime.now() - timedelta(days=30),  # Adjust based on timeframe
            limit=limit
        )
        bars = historical_client.get_stock_bars(request)
        
        # Format response
        result = {}
        for symbol, symbol_bars in bars.items():
            result[symbol] = [{
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            } for bar in symbol_bars]
        
        return result
    except Exception as e:
        logger.error(f"Error getting bars for {symbols}: {e}")
        return {}

def cancel_order(order_id: str) -> bool:
    """
    Cancel an order by ID.
    
    Args:
        order_id: Order ID to cancel
        
    Returns:
        Success status
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return False
    
    try:
        trading_client.cancel_order_by_id(order_id)
        logger.info(f"Order cancelled: {order_id}")
        return True
    except APIError as e:
        logger.error(f"API error cancelling order {order_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return False