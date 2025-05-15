"""
Alpaca client for market data integration.

This module provides functionality for connecting to Alpaca's API
to fetch market data, stream real-time updates, and manage symbols.
"""
import os
import logging
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.models import BarSet, Bar, Quote, Trade

from app import app
from common.db_models import MarketDataModel, WatchlistModel
from app import db

# Configure logger
logger = logging.getLogger(__name__)

# Global variables
trading_client = None
data_client = None
stream_client = None
stream_thread = None
keep_running = True
websocket_connected = False
active_subscriptions = set()
price_callbacks = []


def initialize_clients() -> bool:
    """Initialize Alpaca clients for market data."""
    global trading_client, data_client, stream_client
    
    api_key = os.environ.get("ALPACA_API_KEY", app.config.get("ALPACA_API_KEY", ""))
    api_secret = os.environ.get("ALPACA_API_SECRET", app.config.get("ALPACA_API_SECRET", ""))
    
    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set")
        return False
    
    try:
        # Initialize Trading client for asset info
        trading_client = TradingClient(api_key, api_secret, paper=True)
        
        # Initialize Data client for historical data
        data_client = StockHistoricalDataClient(api_key, api_secret)
        
        # Initialize Stream client for real-time data
        stream_client = StockDataStream(api_key, api_secret)
        
        logger.info("Alpaca clients initialized successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize Alpaca clients: {e}")
        return False


def get_tradable_assets(asset_type: str = "us_equity", status: str = "active") -> List[Dict[str, Any]]:
    """Get list of tradable assets from Alpaca."""
    if not trading_client:
        if not initialize_clients():
            return []
    
    try:
        # Map asset_type string to AssetClass enum
        asset_class = AssetClass.US_EQUITY
        if asset_type.lower() == "crypto":
            asset_class = AssetClass.CRYPTO
        
        # Map status string to AssetStatus enum
        asset_status = AssetStatus.ACTIVE
        if status.lower() == "inactive":
            asset_status = AssetStatus.INACTIVE
        
        # Create request parameters
        params = GetAssetsRequest(
            asset_class=asset_class,
            status=asset_status
        )
        
        # Get assets
        assets = trading_client.get_all_assets(params)
        
        # Convert to dictionaries
        asset_list = []
        for asset in assets:
            asset_dict = {
                "id": asset.id,
                "class": asset.asset_class.value,
                "symbol": asset.symbol,
                "name": asset.name,
                "exchange": asset.exchange,
                "status": asset.status.value,
                "tradable": asset.tradable,
                "marginable": asset.marginable,
                "shortable": asset.shortable,
                "easy_to_borrow": asset.easy_to_borrow,
                "fractionable": asset.fractionable
            }
            asset_list.append(asset_dict)
        
        return asset_list
    
    except Exception as e:
        logger.error(f"Failed to get tradable assets: {e}")
        return []


def get_latest_bars(symbols: List[str]) -> Dict[str, Any]:
    """Get latest bars for a list of symbols."""
    if not data_client:
        if not initialize_clients():
            return {}
    
    try:
        # Create request for latest bars
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame.Minute,
            limit=1
        )
        
        # Get bars
        bars = data_client.get_stock_bars(request)
        
        # Convert to dictionary
        result = {}
        for symbol, bar_data in bars.data.items():
            if bar_data:
                bar = bar_data[0]
                result[symbol] = {
                    "symbol": symbol,
                    "timestamp": bar.timestamp.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "trade_count": bar.trade_count,
                    "vwap": bar.vwap
                }
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get latest bars: {e}")
        return {}


def get_latest_quotes(symbols: List[str]) -> Dict[str, Any]:
    """Get latest quotes for a list of symbols."""
    if not data_client:
        if not initialize_clients():
            return {}
    
    try:
        # Get latest quotes
        quotes = data_client.get_stock_latest_quote(symbol_or_symbols=symbols)
        
        # Convert to dictionary
        result = {}
        for symbol, quote_data in quotes.data.items():
            result[symbol] = {
                "symbol": symbol,
                "timestamp": quote_data.timestamp.isoformat(),
                "ask_price": quote_data.ask_price,
                "ask_size": quote_data.ask_size,
                "bid_price": quote_data.bid_price,
                "bid_size": quote_data.bid_size,
                "mid_price": (quote_data.ask_price + quote_data.bid_price) / 2 if quote_data.ask_price and quote_data.bid_price else None
            }
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get latest quotes: {e}")
        return {}


def get_historical_bars(symbol: str, timeframe: str = 'day', start: Optional[datetime] = None, end: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get historical bars for a symbol."""
    if not data_client:
        if not initialize_clients():
            return []
    
    try:
        # Set default start/end dates if not provided
        if not end:
            end = datetime.now()
        if not start:
            start = end - timedelta(days=30)
        
        # Map timeframe string to TimeFrame enum
        tf = TimeFrame.Day
        if timeframe.lower() == 'minute':
            tf = TimeFrame.Minute
        elif timeframe.lower() == 'hour':
            tf = TimeFrame.Hour
        elif timeframe.lower() == 'week':
            tf = TimeFrame.Week
        elif timeframe.lower() == 'month':
            tf = TimeFrame.Month
        
        # Create request
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit
        )
        
        # Get bars
        bars = data_client.get_stock_bars(request)
        
        # Convert to list of dictionaries
        result = []
        for bar in bars.data.get(symbol, []):
            bar_dict = {
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "trade_count": bar.trade_count,
                "vwap": bar.vwap
            }
            result.append(bar_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get historical bars: {e}")
        return []


def start_stream():
    """Start the market data stream."""
    global keep_running, stream_thread
    
    # If the stream is already running, return
    if stream_thread and stream_thread.is_alive():
        return
    
    # Set flag to keep running
    keep_running = True
    
    # Create and start the stream thread
    stream_thread = threading.Thread(target=_run_stream)
    stream_thread.daemon = True
    stream_thread.start()
    
    logger.info("Market data stream started")


def stop_stream():
    """Stop the market data stream."""
    global keep_running, stream_thread, websocket_connected
    
    # Set flag to stop running
    keep_running = False
    
    # If the stream is running, wait for it to stop
    if stream_thread and stream_thread.is_alive():
        stream_thread.join(timeout=5)
        
    # Reset variables
    stream_thread = None
    websocket_connected = False
    
    logger.info("Market data stream stopped")


def subscribe_to_trades(symbols: List[str]):
    """Subscribe to trade updates for a list of symbols."""
    if not stream_client:
        if not initialize_clients():
            return
    
    # If the stream is not running, start it
    if not stream_thread or not stream_thread.is_alive():
        start_stream()
    
    # Update active subscriptions
    for symbol in symbols:
        active_subscriptions.add(f"trades.{symbol}")
    
    # If the websocket is connected, subscribe to the new symbols
    if websocket_connected:
        try:
            asyncio.run_coroutine_threadsafe(_async_subscribe(), asyncio.get_event_loop())
        except Exception as e:
            logger.error(f"Failed to subscribe to trades: {e}")


def subscribe_to_quotes(symbols: List[str]):
    """Subscribe to quote updates for a list of symbols."""
    if not stream_client:
        if not initialize_clients():
            return
    
    # If the stream is not running, start it
    if not stream_thread or not stream_thread.is_alive():
        start_stream()
    
    # Update active subscriptions
    for symbol in symbols:
        active_subscriptions.add(f"quotes.{symbol}")
    
    # If the websocket is connected, subscribe to the new symbols
    if websocket_connected:
        try:
            asyncio.run_coroutine_threadsafe(_async_subscribe(), asyncio.get_event_loop())
        except Exception as e:
            logger.error(f"Failed to subscribe to quotes: {e}")


def subscribe_to_bars(symbols: List[str]):
    """Subscribe to bar updates for a list of symbols."""
    if not stream_client:
        if not initialize_clients():
            return
    
    # If the stream is not running, start it
    if not stream_thread or not stream_thread.is_alive():
        start_stream()
    
    # Update active subscriptions
    for symbol in symbols:
        active_subscriptions.add(f"bars.{symbol}")
    
    # If the websocket is connected, subscribe to the new symbols
    if websocket_connected:
        try:
            asyncio.run_coroutine_threadsafe(_async_subscribe(), asyncio.get_event_loop())
        except Exception as e:
            logger.error(f"Failed to subscribe to bars: {e}")


def register_price_callback(callback: Callable[[str, float], None]):
    """Register a callback function to be called when a price update is received."""
    price_callbacks.append(callback)


async def _async_subscribe():
    """Subscribe to active subscriptions asynchronously."""
    global stream_client
    
    try:
        # Convert set to list for alpaca-py
        subscriptions = list(active_subscriptions)
        
        # Subscribe to trades/quotes/bars
        if subscriptions:
            logger.info(f"Subscribing to: {subscriptions}")
            await stream_client.subscribe(subscriptions)
    
    except Exception as e:
        logger.error(f"Error in _async_subscribe: {e}")


def _process_trade(trade_data: Trade):
    """Process a trade message from the stream."""
    try:
        symbol = trade_data.symbol
        price = trade_data.price
        
        # Update market data in database
        with app.app_context():
            # Create new market data entry
            market_data = MarketDataModel()
            market_data.symbol = symbol
            market_data.price = price
            market_data.timestamp = datetime.now()
            
            # Try to get previous close for the symbol
            previous_record = db.session.query(MarketDataModel).filter(
                MarketDataModel.symbol == symbol
            ).order_by(
                MarketDataModel.timestamp.desc()
            ).first()
            
            if previous_record:
                market_data.previous_close = previous_record.price
            
            # Add to database
            db.session.add(market_data)
            db.session.commit()
        
        # Call registered callbacks
        for callback in price_callbacks:
            try:
                callback(symbol, price)
            except Exception as e:
                logger.error(f"Error in price callback: {e}")
        
    except Exception as e:
        logger.error(f"Error processing trade: {e}")


def _process_quote(quote_data: Quote):
    """Process a quote message from the stream."""
    try:
        symbol = quote_data.symbol
        ask_price = quote_data.ask_price
        bid_price = quote_data.bid_price
        
        # Update market data in database (using mid price)
        if ask_price is not None and bid_price is not None:
            mid_price = (ask_price + bid_price) / 2
            
            with app.app_context():
                # Create new market data entry
                market_data = MarketDataModel()
                market_data.symbol = symbol
                market_data.price = mid_price
                market_data.timestamp = datetime.now()
                
                # Try to get previous close for the symbol
                previous_record = db.session.query(MarketDataModel).filter(
                    MarketDataModel.symbol == symbol
                ).order_by(
                    MarketDataModel.timestamp.desc()
                ).first()
                
                if previous_record:
                    market_data.previous_close = previous_record.price
                
                # Add to database
                db.session.add(market_data)
                db.session.commit()
            
            # Call registered callbacks
            for callback in price_callbacks:
                try:
                    callback(symbol, mid_price)
                except Exception as e:
                    logger.error(f"Error in price callback: {e}")
    
    except Exception as e:
        logger.error(f"Error processing quote: {e}")


def _process_bar(bar_data: Bar):
    """Process a bar message from the stream."""
    try:
        symbol = bar_data.symbol
        close_price = bar_data.close
        
        # Update market data in database
        with app.app_context():
            # Create new market data entry
            market_data = MarketDataModel()
            market_data.symbol = symbol
            market_data.price = close_price
            market_data.timestamp = datetime.now()
            market_data.volume = bar_data.volume
            
            # Try to get previous close for the symbol
            previous_record = db.session.query(MarketDataModel).filter(
                MarketDataModel.symbol == symbol
            ).order_by(
                MarketDataModel.timestamp.desc()
            ).first()
            
            if previous_record:
                market_data.previous_close = previous_record.price
            
            # Add to database
            db.session.add(market_data)
            db.session.commit()
        
        # Call registered callbacks
        for callback in price_callbacks:
            try:
                callback(symbol, close_price)
            except Exception as e:
                logger.error(f"Error in price callback: {e}")
    
    except Exception as e:
        logger.error(f"Error processing bar: {e}")


async def _handle_stream():
    """Handle the market data stream."""
    global websocket_connected, stream_client
    
    try:
        # Connect to the stream
        logger.info("Connecting to market data stream")
        await stream_client.connect()
        websocket_connected = True
        logger.info("Connected to market data stream")
        
        # Subscribe to active symbols
        await _async_subscribe()
        
        # Set up handlers
        stream_client.subscribe_trade_updates(_process_trade)
        stream_client.subscribe_quote_updates(_process_quote)
        stream_client.subscribe_bars(_process_bar)
        
        # Keep the connection alive
        while keep_running:
            await asyncio.sleep(1)
        
        # Disconnect when done
        await stream_client.close()
        websocket_connected = False
        logger.info("Disconnected from market data stream")
    
    except Exception as e:
        websocket_connected = False
        logger.error(f"Error in market data stream: {e}")


def _run_stream():
    """Run the market data stream in a separate thread."""
    if not stream_client:
        if not initialize_clients():
            return
    
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the stream handler
        loop.run_until_complete(_handle_stream())
    
    except Exception as e:
        logger.error(f"Error in market data stream thread: {e}")


def add_symbols_to_watchlist(symbols: List[str]) -> int:
    """Add symbols to the watchlist."""
    if not isinstance(symbols, list):
        symbols = [symbols]
    
    added_count = 0
    
    try:
        with app.app_context():
            # Get existing symbols in watchlist
            existing = set(item.symbol for item in db.session.query(WatchlistModel).all())
            
            # Add new symbols
            for symbol in symbols:
                if symbol.upper() not in existing:
                    watchlist_item = WatchlistModel()
                    watchlist_item.symbol = symbol.upper()
                    db.session.add(watchlist_item)
                    added_count += 1
            
            # Commit changes
            db.session.commit()
        
        # Subscribe to new symbols
        if added_count > 0:
            subscribe_to_trades(symbols)
            subscribe_to_quotes(symbols)
            subscribe_to_bars(symbols)
        
        return added_count
    
    except Exception as e:
        logger.error(f"Failed to add symbols to watchlist: {e}")
        return 0


def remove_symbols_from_watchlist(symbols: List[str]) -> int:
    """Remove symbols from the watchlist."""
    if not isinstance(symbols, list):
        symbols = [symbols]
    
    removed_count = 0
    
    try:
        with app.app_context():
            # Remove symbols
            for symbol in symbols:
                result = db.session.query(WatchlistModel).filter(
                    WatchlistModel.symbol == symbol.upper()
                ).delete()
                removed_count += result
            
            # Commit changes
            db.session.commit()
        
        # Update subscriptions (would need to reconnect to properly unsubscribe)
        # For now, just log that symbols were removed
        if removed_count > 0:
            logger.info(f"Removed {removed_count} symbols from watchlist")
        
        return removed_count
    
    except Exception as e:
        logger.error(f"Failed to remove symbols from watchlist: {e}")
        return 0


def get_watchlist() -> List[Dict[str, Any]]:
    """Get the current watchlist with latest prices."""
    try:
        with app.app_context():
            # Get watchlist symbols
            watchlist = db.session.query(WatchlistModel).all()
            
            # Get latest prices for symbols
            symbols = [item.symbol for item in watchlist]
            latest_data = {}
            
            if symbols:
                # Try to get latest quotes
                quotes = get_latest_quotes(symbols)
                
                # If quotes failed, try to get latest bars
                if not quotes:
                    bars = get_latest_bars(symbols)
                    for symbol, bar in bars.items():
                        latest_data[symbol] = {
                            "price": bar["close"],
                            "timestamp": bar["timestamp"]
                        }
                else:
                    for symbol, quote in quotes.items():
                        latest_data[symbol] = {
                            "price": quote["mid_price"] or quote["bid_price"],
                            "timestamp": quote["timestamp"]
                        }
            
            # Build result
            result = []
            for item in watchlist:
                symbol = item.symbol
                data = {
                    "symbol": symbol,
                    "added_at": item.added_at.isoformat() if item.added_at else None,
                    "price": None,
                    "timestamp": None
                }
                
                # Add latest price if available
                if symbol in latest_data:
                    data["price"] = latest_data[symbol]["price"]
                    data["timestamp"] = latest_data[symbol]["timestamp"]
                
                result.append(data)
            
            return result
    
    except Exception as e:
        logger.error(f"Failed to get watchlist: {e}")
        return []