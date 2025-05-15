import os
import logging
import threading
import time
from typing import Dict, Set, Callable
import alpaca_trade_api as tradeapi
from common.utils import publish_event, load_config

# Configure logging
logger = logging.getLogger(__name__)

# Global price feed state
_running = False
_subscribed_symbols: Set[str] = set()
_price_callbacks: Dict[str, Callable] = {}
_last_prices: Dict[str, float] = {}

def start_price_feed() -> bool:
    """Start the Alpaca price feed in a background thread"""
    global _running
    
    if _running:
        logger.info("Price feed already running")
        return True
    
    try:
        # Start in a new thread
        thread = threading.Thread(target=_run_price_feed, daemon=True)
        thread.start()
        
        _running = True
        logger.info("Price feed started")
        return True
    except Exception as e:
        logger.error(f"Failed to start price feed: {str(e)}")
        return False

def _run_price_feed() -> None:
    """Run the Alpaca WebSocket connection for price updates"""
    config = load_config()
    
    # Initialize Alpaca API
    api = tradeapi.REST(
        key_id=config['alpaca']['api_key'],
        secret_key=config['alpaca']['api_secret'],
        base_url=config['alpaca']['base_url'],
        api_version='v2'
    )
    
    # Check if API keys are valid
    try:
        account = api.get_account()
        logger.info(f"Connected to Alpaca account: {account.id} (Paper: {account.status == 'ACTIVE'})")
    except Exception as e:
        logger.error(f"Alpaca API connection failed: {str(e)}")
        return
    
    # Set up WebSocket connection
    conn = tradeapi.Stream(
        key_id=config['alpaca']['api_key'],
        secret_key=config['alpaca']['api_secret'],
        base_url=config['alpaca']['base_url'],
        data_feed='iex'  # Use IEX data feed
    )
    
    # Define handlers
    @conn.on_bar('*')
    async def on_bar(bar):
        # Process bar update
        symbol = bar.symbol
        price = bar.close
        
        # Update last price
        _last_prices[symbol] = price
        
        # Publish price update
        publish_event("market.price", {
            "symbol": symbol,
            "price": price,
            "volume": bar.volume,
            "timestamp": bar.timestamp
        })
        
        # Call any registered callbacks for this symbol
        if symbol in _price_callbacks:
            try:
                _price_callbacks[symbol](symbol, price)
            except Exception as e:
                logger.error(f"Error in price callback for {symbol}: {str(e)}")
    
    @conn.on_status("*")
    async def on_status(status):
        logger.info(f"Connection status: {status}")
    
    @conn.on_error("*")
    async def on_error(error):
        logger.error(f"WebSocket error: {error}")
    
    # Start the connection
    try:
        # Subscribe to initial symbols if any
        if _subscribed_symbols:
            symbols = list(_subscribed_symbols)
            conn.subscribe_bars(symbols)
            logger.info(f"Subscribed to {len(symbols)} symbols: {', '.join(symbols)}")
        
        # Start the WebSocket connection
        conn.run()
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        
        # Fall back to polling mode for development/testing
        logger.info("Falling back to polling mode")
        _run_polling_fallback(api)

def _run_polling_fallback(api) -> None:
    """Fallback to polling when WebSocket fails"""
    logger.warning("Using polling fallback for price updates - not recommended for production")
    
    while _running:
        try:
            # If we have subscribed symbols, poll them
            if _subscribed_symbols:
                symbols = list(_subscribed_symbols)
                bars = api.get_barset(symbols, 'minute', 1)
                
                for symbol in symbols:
                    if symbol in bars and len(bars[symbol]) > 0:
                        bar = bars[symbol][0]
                        price = bar.c  # Close price
                        
                        # Update last price
                        _last_prices[symbol] = price
                        
                        # Publish price update
                        publish_event("market.price", {
                            "symbol": symbol,
                            "price": price,
                            "volume": bar.v,
                            "timestamp": bar.t.isoformat()
                        })
                        
                        # Call any registered callbacks
                        if symbol in _price_callbacks:
                            try:
                                _price_callbacks[symbol](symbol, price)
                            except Exception as e:
                                logger.error(f"Error in price callback for {symbol}: {str(e)}")
            
            # Sleep for 1 minute
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in polling update: {str(e)}")
            time.sleep(60)  # Sleep on error and try again

def subscribe_symbol(symbol: str, callback=None) -> bool:
    """Subscribe to price updates for a symbol"""
    global _subscribed_symbols, _price_callbacks
    
    try:
        # Add to set of subscribed symbols
        _subscribed_symbols.add(symbol)
        
        # Store callback if provided
        if callback:
            _price_callbacks[symbol] = callback
        
        logger.info(f"Subscribed to symbol: {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error subscribing to {symbol}: {str(e)}")
        return False

def unsubscribe_symbol(symbol: str) -> bool:
    """Unsubscribe from price updates for a symbol"""
    global _subscribed_symbols, _price_callbacks
    
    try:
        # Remove from set of subscribed symbols
        if symbol in _subscribed_symbols:
            _subscribed_symbols.remove(symbol)
        
        # Remove callback if exists
        if symbol in _price_callbacks:
            del _price_callbacks[symbol]
        
        logger.info(f"Unsubscribed from symbol: {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error unsubscribing from {symbol}: {str(e)}")
        return False

def get_last_price(symbol: str) -> float:
    """Get the last known price for a symbol"""
    global _last_prices
    
    # Return cached price if available
    if symbol in _last_prices:
        return _last_prices[symbol]
    
    # Otherwise fetch current price
    try:
        config = load_config()
        
        # Initialize Alpaca API
        api = tradeapi.REST(
            key_id=config['alpaca']['api_key'],
            secret_key=config['alpaca']['api_secret'],
            base_url=config['alpaca']['base_url'],
            api_version='v2'
        )
        
        # Get last trade
        last_trade = api.get_latest_trade(symbol)
        price = last_trade.price
        
        # Cache the price
        _last_prices[symbol] = price
        
        return price
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {str(e)}")
        return 0.0

def get_subscribed_symbols() -> Set[str]:
    """Get the set of currently subscribed symbols"""
    return _subscribed_symbols.copy()
