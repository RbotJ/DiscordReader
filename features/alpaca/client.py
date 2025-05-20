"""
Alpaca Client Module

This module provides a centralized interface to the Alpaca API clients
for trading, market data, and account management.
"""
import os
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta, timezone

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest, GetOrdersRequest
from alpaca.trading.enums import AssetClass, AssetStatus, OrderStatus, OrderSide, OrderType, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestBarRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')
ALPACA_PAPER = os.environ.get('ALPACA_PAPER', 'true').lower() == 'true'

# Global clients
_trading_client = None
_stock_data_client = None
_option_data_client = None
_crypto_data_client = None

def initialize_clients() -> bool:
    """
    Initialize all Alpaca API clients.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _trading_client, _stock_data_client, _option_data_client, _crypto_data_client
    
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.warning("Alpaca API credentials not found in environment variables")
        return False
        
    try:
        # Initialize trading client
        _trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=ALPACA_PAPER)
        
        # Initialize data clients
        _stock_data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        _option_data_client = OptionHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        _crypto_data_client = CryptoHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
        
        logger.info("Alpaca clients initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Alpaca clients: {e}")
        return False

def get_trading_client() -> Optional[TradingClient]:
    """
    Get the Alpaca trading client.
    
    Returns:
        TradingClient or None if not initialized
    """
    global _trading_client
    
    if _trading_client is None:
        initialize_clients()
        
    return _trading_client

def get_stock_data_client() -> Optional[StockHistoricalDataClient]:
    """
    Get the Alpaca stock historical data client.
    
    Returns:
        StockHistoricalDataClient or None if not initialized
    """
    global _stock_data_client
    
    if _stock_data_client is None:
        initialize_clients()
        
    return _stock_data_client

def get_option_data_client() -> Optional[OptionHistoricalDataClient]:
    """
    Get the Alpaca option historical data client.
    
    Returns:
        OptionHistoricalDataClient or None if not initialized
    """
    global _option_data_client
    
    if _option_data_client is None:
        initialize_clients()
        
    return _option_data_client

def get_crypto_data_client() -> Optional[CryptoHistoricalDataClient]:
    """
    Get the Alpaca crypto historical data client.
    
    Returns:
        CryptoHistoricalDataClient or None if not initialized
    """
    global _crypto_data_client
    
    if _crypto_data_client is None:
        initialize_clients()
        
    return _crypto_data_client

def get_account() -> Optional[Dict]:
    """
    Get account information.
    
    Returns:
        Account information or None if error
    """
    client = get_trading_client()
    if not client:
        logger.warning("Trading client not initialized")
        return None
        
    try:
        account = client.get_account()
        return {
            'id': account.id,
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'equity': float(account.equity),
            'long_market_value': float(account.long_market_value),
            'short_market_value': float(account.short_market_value),
            'initial_margin': float(account.initial_margin),
            'maintenance_margin': float(account.maintenance_margin),
            'daytrading_buying_power': float(account.daytrading_buying_power),
            'status': account.status,
            'is_pattern_day_trader': account.pattern_day_trader,
            'trading_blocked': account.trading_blocked,
            'transfers_blocked': account.transfers_blocked,
            'account_blocked': account.account_blocked,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'currency': account.currency,
            'last_equity': float(account.last_equity) if account.last_equity else None,
            'last_maintenance_margin': float(account.last_maintenance_margin) if account.last_maintenance_margin else None,
            'multiplier': account.multiplier
        }
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        return None

def get_positions() -> List[Dict]:
    """
    Get all positions.
    
    Returns:
        List of positions or empty list if error
    """
    client = get_trading_client()
    if not client:
        logger.warning("Trading client not initialized")
        return []
        
    try:
        positions = client.get_all_positions()
        return [{
            'symbol': pos.symbol,
            'qty': float(pos.qty),
            'avg_entry_price': float(pos.avg_entry_price),
            'market_value': float(pos.market_value),
            'cost_basis': float(pos.cost_basis),
            'unrealized_pl': float(pos.unrealized_pl),
            'unrealized_plpc': float(pos.unrealized_plpc),
            'current_price': float(pos.current_price),
            'lastday_price': float(pos.lastday_price) if pos.lastday_price else None,
            'change_today': float(pos.change_today) if pos.change_today else None,
            'asset_id': pos.asset_id,
            'asset_class': pos.asset_class,
            'side': pos.side
        } for pos in positions]
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []

def get_orders(status: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """
    Get orders.
    
    Args:
        status: Order status filter (optional)
        limit: Maximum number of orders to return
        
    Returns:
        List of orders or empty list if error
    """
    client = get_trading_client()
    if not client:
        logger.warning("Trading client not initialized")
        return []
        
    try:
        request = GetOrdersRequest(limit=limit)
        if status:
            request.status = OrderStatus(status)
            
        orders = client.get_orders(request)
        return [{
            'id': order.id,
            'client_order_id': order.client_order_id,
            'symbol': order.symbol,
            'asset_class': order.asset_class,
            'qty': float(order.qty) if order.qty else None,
            'filled_qty': float(order.filled_qty) if order.filled_qty else None,
            'type': order.type.name if order.type else None,
            'side': order.side.name if order.side else None,
            'time_in_force': order.time_in_force.name if order.time_in_force else None,
            'limit_price': float(order.limit_price) if order.limit_price else None,
            'stop_price': float(order.stop_price) if order.stop_price else None,
            'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
            'status': order.status.name if order.status else None,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
            'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
            'filled_at': order.filled_at.isoformat() if order.filled_at else None,
            'expired_at': order.expired_at.isoformat() if order.expired_at else None,
            'canceled_at': order.canceled_at.isoformat() if order.canceled_at else None,
            'failed_at': order.failed_at.isoformat() if order.failed_at else None,
            'replaced_at': order.replaced_at.isoformat() if order.replaced_at else None,
            'replaced_by': order.replaced_by,
            'replaces': order.replaces,
            'extended_hours': order.extended_hours
        } for order in orders]
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return []

def get_market_clock() -> Optional[Dict]:
    """
    Get market clock information.
    
    Returns:
        Market clock information or None if error
    """
    client = get_trading_client()
    if not client:
        logger.warning("Trading client not initialized")
        return None
        
    try:
        clock = client.get_clock()
        return {
            'timestamp': clock.timestamp.isoformat() if clock.timestamp else None,
            'is_open': clock.is_open,
            'next_open': clock.next_open.isoformat() if clock.next_open else None,
            'next_close': clock.next_close.isoformat() if clock.next_close else None
        }
    except Exception as e:
        logger.error(f"Error getting market clock: {e}")
        return None

def get_latest_bars(symbols: Union[str, List[str]], timeframe: str = '1Min') -> Dict[str, Dict]:
    """
    Get the latest bars for one or more symbols.
    
    Args:
        symbols: Symbol or list of symbols
        timeframe: Bar timeframe
        
    Returns:
        Dictionary mapping symbols to bar data
    """
    client = get_stock_data_client()
    if not client:
        logger.warning("Stock data client not initialized")
        return {}
        
    # Convert single symbol to list
    if isinstance(symbols, str):
        symbols = [symbols]
        
    # Parse timeframe
    if timeframe.endswith('Min'):
        minutes = int(timeframe[:-3])
        tf = TimeFrame.Minute(minutes)
    elif timeframe.endswith('Hour'):
        hours = int(timeframe[:-4])
        tf = TimeFrame.Hour(hours)
    elif timeframe.endswith('Day'):
        days = int(timeframe[:-3])
        tf = TimeFrame.Day(days)
    else:
        logger.warning(f"Unknown timeframe: {timeframe}, using 1Min")
        tf = TimeFrame.Minute(1)
        
    try:
        # Create request
        request = StockLatestBarRequest(symbol_or_symbols=symbols)
        
        # Get bars
        bars = client.get_stock_latest_bar(request)
        
        # Format bars
        result = {}
        for symbol, bar in bars.items():
            result[symbol] = {
                'symbol': symbol,
                'timestamp': bar.timestamp.isoformat() if bar.timestamp else None,
                'open': float(bar.open) if bar.open else None,
                'high': float(bar.high) if bar.high else None,
                'low': float(bar.low) if bar.low else None,
                'close': float(bar.close) if bar.close else None,
                'volume': int(bar.volume) if bar.volume else 0,
                'timeframe': timeframe
            }
            
        return result
    except Exception as e:
        logger.error(f"Error getting latest bars: {e}")
        return {}

def get_latest_quotes(symbols: Union[str, List[str]]) -> Dict[str, Dict]:
    """
    Get the latest quotes for one or more symbols.
    
    Args:
        symbols: Symbol or list of symbols
        
    Returns:
        Dictionary mapping symbols to quote data
    """
    client = get_stock_data_client()
    if not client:
        logger.warning("Stock data client not initialized")
        return {}
        
    # Convert single symbol to list
    if isinstance(symbols, str):
        symbols = [symbols]
        
    try:
        # Create request
        request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
        
        # Get quotes
        quotes = client.get_stock_latest_quote(request)
        
        # Format quotes
        result = {}
        for symbol, quote in quotes.items():
            result[symbol] = {
                'symbol': symbol,
                'timestamp': quote.timestamp.isoformat() if quote.timestamp else None,
                'ask_price': float(quote.ask_price) if quote.ask_price else None,
                'ask_size': int(quote.ask_size) if quote.ask_size else 0,
                'bid_price': float(quote.bid_price) if quote.bid_price else None,
                'bid_size': int(quote.bid_size) if quote.bid_size else 0
            }
            
            # Calculate mid price
            if result[symbol]['ask_price'] and result[symbol]['bid_price']:
                result[symbol]['mid_price'] = (result[symbol]['ask_price'] + result[symbol]['bid_price']) / 2
            else:
                result[symbol]['mid_price'] = None
                
        return result
    except Exception as e:
        logger.error(f"Error getting latest quotes: {e}")
        return {}

def get_bars(
    symbol: str,
    timeframe: str = '5Min',
    start: Optional[Union[str, datetime]] = None,
    end: Optional[Union[str, datetime]] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Get historical bars for a symbol.
    
    Args:
        symbol: Symbol to get bars for
        timeframe: Bar timeframe
        start: Start date/time (optional)
        end: End date/time (optional)
        limit: Maximum number of bars to return
        
    Returns:
        List of bar dictionaries
    """
    client = get_stock_data_client()
    if not client:
        logger.warning("Stock data client not initialized")
        return []
        
    # Parse timeframe
    if timeframe.endswith('Min'):
        minutes = int(timeframe[:-3])
        tf = TimeFrame.Minute(minutes)
    elif timeframe.endswith('Hour'):
        hours = int(timeframe[:-4])
        tf = TimeFrame.Hour(hours)
    elif timeframe.endswith('Day'):
        days = int(timeframe[:-3])
        tf = TimeFrame.Day(days)
    else:
        logger.warning(f"Unknown timeframe: {timeframe}, using 5Min")
        tf = TimeFrame.Minute(5)
        
    # Set default start/end times if not provided
    if end is None:
        end = datetime.now(timezone.utc)
    elif isinstance(end, str):
        end = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
    if start is None:
        # Calculate start time based on timeframe and limit
        if timeframe.endswith('Min'):
            minutes = int(timeframe[:-3])
            start = end - timedelta(minutes=minutes * limit)
        elif timeframe.endswith('Hour'):
            hours = int(timeframe[:-4])
            start = end - timedelta(hours=hours * limit)
        elif timeframe.endswith('Day'):
            days = int(timeframe[:-3])
            start = end - timedelta(days=days * limit)
        else:
            start = end - timedelta(minutes=5 * limit)
    elif isinstance(start, str):
        start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        
    try:
        # Create request
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
            adjustment=Adjustment.ALL
        )
        
        # Get bars
        bars = client.get_stock_bars(request)
        
        # Check if symbol is in response
        if not bars or symbol not in bars:
            logger.warning(f"No data returned for {symbol}")
            return []
            
        # Format bars
        result = []
        for bar in bars[symbol]:
            result.append({
                'symbol': symbol,
                'timestamp': bar.timestamp.isoformat() if bar.timestamp else None,
                'open': float(bar.open) if bar.open else None,
                'high': float(bar.high) if bar.high else None,
                'low': float(bar.low) if bar.low else None,
                'close': float(bar.close) if bar.close else None,
                'volume': int(bar.volume) if bar.volume else 0,
                'timeframe': timeframe
            })
            
        # Sort by timestamp (newest last)
        result.sort(key=lambda x: x['timestamp'])
        
        return result
    except Exception as e:
        logger.error(f"Error getting bars for {symbol}: {e}")
        return []

def alpaca_market_client() -> Optional[StockHistoricalDataClient]:
    """Alias for get_stock_data_client() for backward compatibility."""
    return get_stock_data_client()

# Initialize clients on module import
initialize_clients()