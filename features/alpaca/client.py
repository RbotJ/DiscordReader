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
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
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

# Export client instances for use by other modules
alpaca_trading_client = None
alpaca_market_client = None

def initialize_clients():
    """Initialize Alpaca clients if credentials are available."""
    global trading_client, historical_client, alpaca_trading_client, alpaca_market_client
    
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return False
    
    try:
        # Initialize trading client for paper trading
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True)
        
        # Initialize historical data client
        historical_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        
        # Set the exported client references
        alpaca_trading_client = trading_client
        alpaca_market_client = historical_client
        
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
        
        # Manual extraction to avoid serialization issues
        return {
            'id': str(account.id) if hasattr(account, 'id') else '',
            'status': str(account.status) if hasattr(account, 'status') else '',
            'equity': float(account.equity) if hasattr(account, 'equity') else 0,
            'cash': float(account.cash) if hasattr(account, 'cash') else 0,
            'buying_power': float(account.buying_power) if hasattr(account, 'buying_power') else 0,
            'position_market_value': float(account.long_market_value or 0) - float(account.short_market_value or 0),
            'portfolio_value': float(account.portfolio_value) if hasattr(account, 'portfolio_value') else 0,
            'trading_blocked': bool(account.trading_blocked) if hasattr(account, 'trading_blocked') else False,
            'pattern_day_trader': bool(account.pattern_day_trader) if hasattr(account, 'pattern_day_trader') else False,
            'account_number': str(account.account_number) if hasattr(account, 'account_number') else '',
            'created_at': str(account.created_at) if hasattr(account, 'created_at') else ''
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
        # Get all positions from the Alpaca API
        positions = trading_client.get_all_positions()
        position_list = []
        
        for pos in positions:
            # Extract properties directly to avoid serialization issues
            try:
                # Check if position is positive for 'long' or negative for 'short'
                qty = float(pos.qty) if hasattr(pos, 'qty') else 0
                
                position_list.append({
                    'symbol': str(pos.symbol) if hasattr(pos, 'symbol') else '',
                    'qty': qty,
                    'market_value': float(pos.market_value) if hasattr(pos, 'market_value') else 0,
                    'avg_entry_price': float(pos.avg_entry_price) if hasattr(pos, 'avg_entry_price') else 0,
                    'side': 'long' if qty > 0 else 'short',
                    'unrealized_pl': float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0,
                    'unrealized_plpc': float(pos.unrealized_plpc) if hasattr(pos, 'unrealized_plpc') else 0,
                    'current_price': float(pos.current_price) if hasattr(pos, 'current_price') else 0,
                    'asset_id': str(pos.asset_id) if hasattr(pos, 'asset_id') else '',
                    'asset_class': str(pos.asset_class) if hasattr(pos, 'asset_class') else '',
                    'lastday_price': float(pos.lastday_price) if hasattr(pos, 'lastday_price') else 0
                })
            except Exception as e:
                logger.error(f"Error processing position {pos}: {e}")
                continue
                
        return position_list
    except AttributeError:
        # Implement a fallback method for different client versions
        try:
            # For newer Alpaca SDK versions that might not have get_all_positions
            positions = trading_client.get_positions()
            position_list = []
            
            for pos in positions:
                # Extract position data
                try:
                    # Check if position is positive for 'long' or negative for 'short'
                    qty = float(pos.qty) if hasattr(pos, 'qty') else 0
                    
                    position_list.append({
                        'symbol': str(pos.symbol) if hasattr(pos, 'symbol') else '',
                        'qty': qty,
                        'market_value': float(pos.market_value) if hasattr(pos, 'market_value') else 0,
                        'avg_entry_price': float(pos.avg_entry_price) if hasattr(pos, 'avg_entry_price') else 0,
                        'side': 'long' if qty > 0 else 'short',
                        'unrealized_pl': float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0,
                        'unrealized_plpc': float(pos.unrealized_plpc) if hasattr(pos, 'unrealized_plpc') else 0,
                        'current_price': float(pos.current_price) if hasattr(pos, 'current_price') else 0
                    })
                except Exception as e:
                    logger.error(f"Error processing position {pos}: {e}")
                    continue
                    
            return position_list
        except Exception as e:
            logger.error(f"Error getting positions using fallback method: {e}")
            return []
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
        orders = trading_client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
        result = []
        
        for order in orders:
            # Handle each order individually to process properties safely
            try:
                order_data = {
                    'id': str(order.id) if hasattr(order, 'id') else '',
                    'symbol': str(order.symbol) if hasattr(order, 'symbol') else '',
                    'qty': float(order.qty) if hasattr(order, 'qty') else 0,
                    'filled_qty': float(order.filled_qty) if hasattr(order, 'filled_qty') else 0,
                    'status': str(order.status.name) if hasattr(order, 'status') and hasattr(order.status, 'name') else 
                             str(order.status) if hasattr(order, 'status') else 'unknown'
                }
                
                # Handle side property
                if hasattr(order, 'side'):
                    if hasattr(order.side, 'name'):
                        order_data['side'] = str(order.side.name)
                    else:
                        order_data['side'] = str(order.side)
                else:
                    order_data['side'] = 'unknown'
                
                # Handle order type
                if hasattr(order, 'order_type'):
                    if hasattr(order.order_type, 'name'):
                        order_data['type'] = str(order.order_type.name)
                    else:
                        order_data['type'] = str(order.order_type)
                else:
                    order_data['type'] = 'unknown'
                
                # Handle time in force
                if hasattr(order, 'time_in_force'):
                    if hasattr(order.time_in_force, 'name'):
                        order_data['time_in_force'] = str(order.time_in_force.name)
                    else:
                        order_data['time_in_force'] = str(order.time_in_force)
                else:
                    order_data['time_in_force'] = 'day'
                
                # Handle prices
                if hasattr(order, 'limit_price') and order.limit_price:
                    try:
                        order_data['limit_price'] = float(order.limit_price)
                    except (ValueError, TypeError):
                        order_data['limit_price'] = None
                else:
                    order_data['limit_price'] = None
                    
                if hasattr(order, 'stop_price') and order.stop_price:
                    try:
                        order_data['stop_price'] = float(order.stop_price)
                    except (ValueError, TypeError):
                        order_data['stop_price'] = None
                else:
                    order_data['stop_price'] = None
                
                # Handle timestamps
                if hasattr(order, 'submitted_at'):
                    order_data['created_at'] = str(order.submitted_at)
                elif hasattr(order, 'created_at'):
                    order_data['created_at'] = str(order.created_at)
                else:
                    order_data['created_at'] = None
                    
                if hasattr(order, 'updated_at'):
                    order_data['updated_at'] = str(order.updated_at)
                else:
                    order_data['updated_at'] = None
                    
                result.append(order_data)
            except Exception as e:
                logger.error(f"Error processing order {order}: {e}")
                continue
        
        return result
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
        
        # Extract order information safely
        order_id = str(order.id) if hasattr(order, 'id') else ''
        logger.info(f"Market order submitted: {order_id} - {symbol} {qty} {side}")
        
        # Build response dictionary with safe property extraction
        result = {
            'id': order_id,
            'symbol': str(order.symbol) if hasattr(order, 'symbol') else symbol,
            'qty': float(order.qty) if hasattr(order, 'qty') else float(qty),
            'type': 'market',
        }
        
        # Add optional fields when available
        if hasattr(order, 'client_order_id'):
            result['client_order_id'] = str(order.client_order_id) if order.client_order_id else None
        
        # Handle side
        if hasattr(order, 'side'):
            if hasattr(order.side, 'name'):
                result['side'] = str(order.side.name)
            else:
                result['side'] = str(order.side)
        else:
            result['side'] = side
        
        # Handle time in force
        if hasattr(order, 'time_in_force'):
            if hasattr(order.time_in_force, 'name'):
                result['time_in_force'] = str(order.time_in_force.name)
            else:
                result['time_in_force'] = str(order.time_in_force)
        else:
            result['time_in_force'] = time_in_force
        
        # Handle status
        if hasattr(order, 'status'):
            if hasattr(order.status, 'name'):
                result['status'] = str(order.status.name)
            else:
                result['status'] = str(order.status)
        else:
            result['status'] = 'unknown'
        
        # Handle timestamps
        if hasattr(order, 'submitted_at'):
            result['created_at'] = str(order.submitted_at)
        elif hasattr(order, 'created_at'):
            result['created_at'] = str(order.created_at)
        else:
            result['created_at'] = str(datetime.now().isoformat())
        
        return result
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
            'id': str(order.id),
            'client_order_id': str(order.client_order_id) if order.client_order_id else None,
            'symbol': str(order.symbol),
            'qty': float(order.qty),
            'side': str(order.side.name) if hasattr(order.side, 'name') else str(order.side),
            'type': 'limit',
            'limit_price': float(limit_price),
            'time_in_force': str(order.time_in_force.name) if hasattr(order.time_in_force, 'name') else str(order.time_in_force),
            'status': str(order.status.name) if hasattr(order.status, 'name') else str(order.status),
            'created_at': str(order.submitted_at) if hasattr(order, 'submitted_at') else str(order.created_at)
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
            symbol_or_symbols=symbol,
            start=datetime.now() - timedelta(minutes=5),
            end=datetime.now()
        )
        quotes = historical_client.get_stock_quotes(request)
        
        # Check if we have quote data
        if quotes and len(quotes) > 0:
            # Handle different response formats
            if isinstance(quotes, dict) and symbol in quotes:
                # Dictionary format with symbol as key
                quotes_list = quotes[symbol]
                if len(quotes_list) > 0:
                    latest = quotes_list[-1]
                else:
                    return None
            else:
                # Direct list format
                quotes_list = list(quotes)
                if len(quotes_list) > 0:
                    latest = quotes_list[-1]
                else:
                    return None
            
            return {
                'symbol': symbol,
                'ask_price': float(latest.ask_price) if hasattr(latest, 'ask_price') else None,
                'ask_size': int(latest.ask_size) if hasattr(latest, 'ask_size') else None,
                'bid_price': float(latest.bid_price) if hasattr(latest, 'bid_price') else None,
                'bid_size': int(latest.bid_size) if hasattr(latest, 'bid_size') else None,
                'timestamp': str(latest.timestamp) if hasattr(latest, 'timestamp') else None
            }
        else:
            logger.warning(f"No quote data found for {symbol}")
            return None
    except Exception as e:
        logger.error(f"Error getting latest quote for {symbol}: {e}")
        return None

def get_latest_bars(symbols: Union[List[str], str], timeframe: str = '1Day', limit: int = 10) -> Dict[str, List[Dict]]:
    """
    Get the latest bars for symbols.
    
    Args:
        symbols: List of ticker symbols or a single symbol
        timeframe: Bar timeframe ('1Day', '1Hour', '15Min', etc.)
        limit: Number of bars to retrieve
        
    Returns:
        Dictionary of symbol -> list of bar dictionaries
    """
    if not historical_client:
        logger.warning("Historical client not initialized")
        return {}
    
    try:
        # Convert single symbol to list
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # Map timeframe string to TimeFrame enum
        if timeframe == '1Day':
            tf = TimeFrame.DAY
        elif timeframe == '1Hour':
            tf = TimeFrame.HOUR
        elif timeframe == '1Min':
            tf = TimeFrame.MINUTE
        else:
            # Default to day
            tf = TimeFrame.DAY
        
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
        
        # Handle different response formats
        if isinstance(bars, dict):
            # Dictionary format with symbol as key
            for symbol, symbol_bars in bars.items():
                result[symbol] = []
                for bar in symbol_bars:
                    result[symbol].append({
                        'timestamp': str(bar.timestamp) if hasattr(bar, 'timestamp') else None,
                        'open': float(bar.open) if hasattr(bar, 'open') else None,
                        'high': float(bar.high) if hasattr(bar, 'high') else None,
                        'low': float(bar.low) if hasattr(bar, 'low') else None,
                        'close': float(bar.close) if hasattr(bar, 'close') else None,
                        'volume': int(bar.volume) if hasattr(bar, 'volume') else None
                    })
        else:
            # Direct list format or other format
            logger.warning("Unexpected format in get_stock_bars response")
            return {}
        
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

# Initialize clients on module import
initialize_clients()