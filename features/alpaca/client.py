"""
Alpaca Client Module

This module provides the client interface for connecting to Alpaca API
for paper trading and market data.
"""
import os
import logging
import json
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
alpaca_market_client = None  # Alias for data_client

def initialize_clients() -> bool:
    """Initialize Alpaca clients if credentials are available."""
    global trading_client, data_client, alpaca_market_client

    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return False

    try:
        # Initialize trading client for paper trading
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True)

        # Initialize data client
        data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        alpaca_market_client = data_client  # Create alias for compatibility

        logger.info("Alpaca clients initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Alpaca clients: {e}")
        return False

def serialize_object(obj: Any) -> Dict:
    """
    Serialize an Alpaca API object to a dictionary.
    
    Args:
        obj: Alpaca API object
        
    Returns:
        Dictionary representation of the object
    """
    if hasattr(obj, "__dict__"):
        # Convert object to dict if it has __dict__
        return {k: serialize_object(v) for k, v in obj.__dict__.items() 
                if not k.startswith('_')}
    elif hasattr(obj, "dict"):
        # Use .dict() method if available (Pydantic models)
        return obj.dict()
    elif isinstance(obj, dict):
        # Recursively serialize dict values
        return {k: serialize_object(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Recursively serialize list items
        return [serialize_object(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        # Return primitive types as is
        return obj
    else:
        # Try to convert to string for other types
        try:
            return str(obj)
        except:
            return None

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
        return serialize_object(account)
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
        return [serialize_object(p) for p in positions]
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []

def get_orders(status: Optional[str] = 'open') -> List[Dict]:
    """
    Get orders from Alpaca with the specified status.

    Args:
        status: Order status ('open', 'closed', 'all')

    Returns:
        List of order dictionaries
    """
    if not trading_client:
        logger.warning("Trading client not initialized")
        return []

    try:
        # Map status string to enum
        status_enum = None
        if status == 'open':
            status_enum = QueryOrderStatus.OPEN
        elif status == 'closed':
            status_enum = QueryOrderStatus.CLOSED
        
        # Create request
        request = GetOrdersRequest(
            status=status_enum,
            limit=100
        )
        
        # Get orders
        orders = trading_client.get_orders(filter=request)
        return [serialize_object(o) for o in orders]
    except Exception as e:
        logger.error(f"Error getting orders with status {status}: {e}")
        return []

def get_open_orders() -> List[Dict]:
    """
    Get open orders from Alpaca.

    Returns:
        List of order dictionaries
    """
    return get_orders(status='open')

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
        return serialize_object(resp[symbol])
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
        # Create market order request
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit order
        order = trading_client.submit_order(order_data=order_request)
        return serialize_object(order)

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
        order = trading_client.submit_order(order_data=order_data)
        return serialize_object(order)

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
        trading_client.cancel_order_by_id(order_id=order_id)
        logger.info(f"Order cancelled: {order_id}")
        return True
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return False

def get_bars(
    symbol: str,
    timeframe: str = '1Min',
    limit: int = 100
) -> List[Dict]:
    """
    Get historical bars for a symbol.
    
    Args:
        symbol: Ticker symbol
        timeframe: Bar timeframe (e.g., '1Min', '5Min', '15Min', '1Day')
        limit: Maximum number of bars to return
        
    Returns:
        List of bar dictionaries
    """
    if not data_client:
        logger.warning("Data client not initialized")
        return []
        
    try:
        # Map timeframe string to TimeFrame object
        tf = TimeFrame.MINUTE
        if timeframe.endswith('Min'):
            # Extract number of minutes
            mins = int(timeframe[:-3])
            if mins == 1:
                tf = TimeFrame.MINUTE
            elif mins == 5:
                tf = TimeFrame.MINUTE_5
            elif mins == 15:
                tf = TimeFrame.MINUTE_15
            elif mins == 30:
                tf = TimeFrame.MINUTE_30
            else:
                logger.warning(f"Unsupported minute timeframe: {timeframe}, using 1Min")
                tf = TimeFrame.MINUTE
        elif timeframe == '1Hour' or timeframe == '1H':
            tf = TimeFrame.HOUR
        elif timeframe == '1Day' or timeframe == '1D':
            tf = TimeFrame.DAY
        
        # Calculate start and end dates
        end = datetime.now()
        
        # Create request
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            limit=limit,
            adjustment="all"
        )
        
        # Get bars
        response = data_client.get_stock_bars(request)
        
        # Convert to list of dictionaries
        if symbol not in response:
            return []
            
        bars = []
        for bar in response[symbol]:
            bar_dict = serialize_object(bar)
            # Rename timestamp to t for consistency
            if 'timestamp' in bar_dict:
                bar_dict['t'] = bar_dict['timestamp']
            bars.append(bar_dict)
            
        return bars
        
    except Exception as e:
        logger.error(f"Error getting bars for {symbol}: {e}")
        return []

def get_latest_bars(symbol: str, timeframe: str = '1Min', limit: int = 1) -> List[Dict]:
    """
    Get the latest bars for a symbol.
    
    Args:
        symbol: Ticker symbol
        timeframe: Bar timeframe
        limit: Number of latest bars to get
        
    Returns:
        List of bar dictionaries
    """
    return get_bars(symbol, timeframe, limit)

def get_historical_candles(
    symbol: str,
    timeframe: str = '1Min',
    limit: int = 100
) -> List[Dict]:
    """
    Get historical candles for a symbol.
    This is an alias for get_bars for compatibility.
    
    Args:
        symbol: Ticker symbol
        timeframe: Candle timeframe
        limit: Maximum number of candles to return
        
    Returns:
        List of candle dictionaries
    """
    return get_bars(symbol, timeframe, limit)

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
        account = get_account_info()
        buying_power = float(account.get("buying_power", 0))

        # Check if we have enough buying power for minimum risk
        if buying_power < risk_amount:
            logger.warning(f"Insufficient buying power (${buying_power}) for minimum risk (${risk_amount})")
            return 0

        # Fetch latest option quote
        quote = get_latest_quote(symbol)
        if not quote:
            logger.warning(f"Could not get quote for {symbol}")
            return 1

        # Get ask price for conservative sizing
        ask_price = float(quote.get("ask_price", 0))
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