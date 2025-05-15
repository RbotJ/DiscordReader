import logging
import json
import threading
import time
from typing import Dict, List, Any, Optional, Callable
import requests
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from alpaca.data import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.models import Bar, Quote
from common.models import MarketData
from common.redis_utils import RedisClient

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint
market_routes = Blueprint('market', __name__, url_prefix='/api/market')

# Redis channels
PRICE_UPDATE_CHANNEL = "aplus.market.price_update"
TRIGGER_CHANNEL = "aplus.market.trigger"

# In-memory cache of latest prices
latest_prices: Dict[str, float] = {}
# Subscription tracking
active_subscriptions: Dict[str, bool] = {}
# Websocket client
websocket_client = None
# Background thread for websocket
websocket_thread = None
# Watchlist of symbols being monitored
watchlist: List[str] = []
# Price triggers with callbacks
price_triggers: Dict[str, List[Dict[str, Any]]] = {}


def initialize_alpaca_client():
    """Initialize Alpaca API client for market data."""
    global websocket_client
    
    api_key = current_app.config.get("ALPACA_API_KEY", "")
    api_secret = current_app.config.get("ALPACA_API_SECRET", "")
    
    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set. Market data features will not work.")
        return None, None
    
    try:
        # Initialize historical data client
        historical_client = StockHistoricalDataClient(api_key, api_secret)
        
        # Initialize websocket client
        websocket_client = StockDataStream(api_key, api_secret)
        
        return historical_client, websocket_client
    except Exception as e:
        logger.error(f"Error initializing Alpaca client: {str(e)}", exc_info=True)
        return None, None


def start_websocket_thread():
    """Start a background thread for the websocket connection."""
    global websocket_thread
    
    if websocket_thread and websocket_thread.is_alive():
        logger.info("Websocket thread already running")
        return
    
    websocket_thread = threading.Thread(target=run_websocket_client)
    websocket_thread.daemon = True
    websocket_thread.start()
    logger.info("Started websocket thread")


def run_websocket_client():
    """Run the websocket client in a background thread."""
    global websocket_client, active_subscriptions, latest_prices
    
    if not websocket_client:
        logger.error("Websocket client not initialized")
        return
    
    async def _on_trade_update(trade):
        """Handle trade updates from websocket."""
        symbol = trade.symbol
        price = trade.price
        
        # Update latest price
        latest_prices[symbol] = price
        
        # Get Redis client
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = RedisClient(redis_url)
        
        # Create market data object
        market_data = MarketData(
            symbol=symbol,
            price=price,
            timestamp=datetime.now()
        )
        
        # Publish price update
        redis_client.publish(PRICE_UPDATE_CHANNEL, market_data.dict())
        
        # Check price triggers
        check_price_triggers(symbol, price, redis_client)
    
    # Set up the websocket handlers
    websocket_client.subscribe_trades(_on_trade_update, *active_subscriptions.keys())
    
    try:
        websocket_client.run()
    except Exception as e:
        logger.error(f"Websocket error: {str(e)}", exc_info=True)
        # Try to reconnect after a delay
        time.sleep(5)
        run_websocket_client()


def check_price_triggers(symbol: str, price: float, redis_client: RedisClient):
    """Check if the current price triggers any monitored conditions."""
    global price_triggers
    
    if symbol not in price_triggers:
        return
    
    triggers_to_remove = []
    
    for i, trigger in enumerate(price_triggers[symbol]):
        comparison = trigger.get('comparison')
        trigger_price = trigger.get('price')
        
        is_triggered = False
        
        if comparison == 'above' and price >= trigger_price:
            is_triggered = True
        elif comparison == 'below' and price <= trigger_price:
            is_triggered = True
        elif comparison == 'near':
            # Consider 'near' if within 0.5% of the price
            threshold = trigger_price * 0.005
            is_triggered = abs(price - trigger_price) <= threshold
        
        if is_triggered:
            # Mark for removal
            triggers_to_remove.append(i)
            
            # Create trigger event
            trigger_event = {
                'symbol': symbol,
                'price': price,
                'trigger_price': trigger_price,
                'comparison': comparison,
                'trigger_id': trigger.get('id'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Publish the trigger event
            redis_client.publish(TRIGGER_CHANNEL, trigger_event)
            logger.info(f"Price trigger: {symbol} {comparison} {trigger_price} at {price}")
    
    # Remove triggered items (in reverse order to maintain indices)
    for i in sorted(triggers_to_remove, reverse=True):
        price_triggers[symbol].pop(i)


@market_routes.route('/prices', methods=['GET'])
def get_prices():
    """Get latest prices for the watchlist or specific symbols."""
    try:
        symbols = request.args.get('symbols')
        
        # Parse symbols list or use watchlist
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        else:
            symbol_list = watchlist
        
        if not symbol_list:
            return jsonify({"status": "error", "message": "No symbols specified and watchlist is empty"}), 400
        
        # Filter latest prices by the requested symbols
        result = {}
        for symbol in symbol_list:
            result[symbol] = latest_prices.get(symbol)
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "prices": result
        })
        
    except Exception as e:
        logger.error(f"Error getting prices: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@market_routes.route('/watchlist', methods=['GET'])
def get_watchlist():
    """Get the current watchlist."""
    return jsonify({
        "status": "success",
        "count": len(watchlist),
        "symbols": watchlist
    })


@market_routes.route('/watchlist', methods=['POST'])
def update_watchlist():
    """Add symbols to the watchlist and subscribe to price updates."""
    global watchlist, active_subscriptions, websocket_client
    
    try:
        data = request.json
        
        if not data or 'symbols' not in data:
            return jsonify({"status": "error", "message": "Missing symbols field"}), 400
        
        new_symbols = [s.strip().upper() for s in data['symbols']]
        
        if not new_symbols:
            return jsonify({"status": "error", "message": "No symbols provided"}), 400
        
        # Add to watchlist
        for symbol in new_symbols:
            if symbol not in watchlist:
                watchlist.append(symbol)
        
        # Subscribe to price updates
        for symbol in new_symbols:
            if symbol not in active_subscriptions:
                active_subscriptions[symbol] = True
        
        # Initialize Alpaca clients if needed
        if not websocket_client:
            _, websocket_client = initialize_alpaca_client()
            
            if not websocket_client:
                return jsonify({"status": "error", "message": "Failed to initialize Alpaca client"}), 500
        
        # Start websocket thread if needed
        start_websocket_thread()
        
        return jsonify({
            "status": "success",
            "message": f"Added {len(new_symbols)} symbols to watchlist",
            "watchlist": watchlist
        })
        
    except Exception as e:
        logger.error(f"Error updating watchlist: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@market_routes.route('/triggers', methods=['POST'])
def add_price_trigger():
    """Add a price trigger for a symbol."""
    global price_triggers
    
    try:
        data = request.json
        
        if not data or 'symbol' not in data or 'comparison' not in data or 'price' not in data:
            return jsonify({
                "status": "error", 
                "message": "Missing required fields: symbol, comparison, price"
            }), 400
        
        symbol = data['symbol'].strip().upper()
        comparison = data['comparison'].lower()
        price = float(data['price'])
        trigger_id = data.get('id', f"trigger_{datetime.now().timestamp()}")
        
        if comparison not in ['above', 'below', 'near']:
            return jsonify({
                "status": "error", 
                "message": "Invalid comparison type. Must be one of: above, below, near"
            }), 400
        
        # Initialize triggers for this symbol if not exists
        if symbol not in price_triggers:
            price_triggers[symbol] = []
        
        # Add the trigger
        price_triggers[symbol].append({
            'comparison': comparison,
            'price': price,
            'id': trigger_id,
            'created_at': datetime.now().isoformat()
        })
        
        # Add to watchlist if not already there
        if symbol not in watchlist:
            watchlist.append(symbol)
        
        # Subscribe to price updates
        if symbol not in active_subscriptions:
            active_subscriptions[symbol] = True
            
            # Initialize Alpaca clients if needed
            if not websocket_client:
                _, websocket_client = initialize_alpaca_client()
                
                if not websocket_client:
                    return jsonify({"status": "error", "message": "Failed to initialize Alpaca client"}), 500
            
            # Start websocket thread if needed
            start_websocket_thread()
        
        return jsonify({
            "status": "success",
            "message": f"Added price trigger for {symbol}",
            "trigger": {
                "symbol": symbol,
                "comparison": comparison,
                "price": price,
                "id": trigger_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error adding price trigger: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@market_routes.route('/triggers', methods=['GET'])
def get_price_triggers():
    """Get all active price triggers."""
    result = {}
    
    for symbol, triggers in price_triggers.items():
        result[symbol] = triggers
    
    return jsonify({
        "status": "success",
        "count": sum(len(triggers) for triggers in price_triggers.values()),
        "triggers": result
    })


@market_routes.route('/historical/<symbol>', methods=['GET'])
def get_historical_data(symbol):
    """Get historical price data for a symbol."""
    try:
        symbol = symbol.upper()
        
        # Get query parameters
        timeframe = request.args.get('timeframe', 'day')
        limit = int(request.args.get('limit', 10))
        
        # Initialize Alpaca client
        historical_client, _ = initialize_alpaca_client()
        
        if not historical_client:
            return jsonify({"status": "error", "message": "Failed to initialize Alpaca client"}), 500
        
        # Map timeframe string to Alpaca TimeFrame
        if timeframe == '1min':
            tf = TimeFrame.Minute
        elif timeframe == '5min':
            tf = TimeFrame.Minute
            limit = limit * 5  # Get 5x the data for 5min bars
        elif timeframe == '15min':
            tf = TimeFrame.Minute
            limit = limit * 15  # Get 15x the data for 15min bars
        elif timeframe == 'hour':
            tf = TimeFrame.Hour
        elif timeframe == 'day':
            tf = TimeFrame.Day
        else:
            tf = TimeFrame.Day
        
        # Request historical bars
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            limit=limit
        )
        
        bars = historical_client.get_stock_bars(request_params)
        
        if symbol not in bars:
            return jsonify({"status": "error", "message": f"No data found for {symbol}"}), 404
        
        # Format the response
        bar_data = []
        for bar in bars[symbol]:
            bar_data.append({
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume
            })
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(bar_data),
            "bars": bar_data
        })
        
    except Exception as e:
        logger.error(f"Error getting historical data: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
