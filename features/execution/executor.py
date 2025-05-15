import logging
import json
import uuid
import threading
import time
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request, current_app
from alpaca.trading import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from common.models import TradeOrder, Position
from common.utils import generate_client_order_id
from common.redis_utils import RedisClient

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint
execution_routes = Blueprint('execution', __name__, url_prefix='/api/execution')

# Redis channels
SIGNAL_TRIGGERED_CHANNEL = "aplus.strategy.signal_triggered"
ORDER_PLACED_CHANNEL = "aplus.execution.order_placed"
ORDER_FILLED_CHANNEL = "aplus.execution.order_filled"
POSITION_UPDATE_CHANNEL = "aplus.execution.position_update"

# Background thread for subscription
subscription_thread = None
is_running = False


def initialize_trading_client():
    """Initialize Alpaca Trading client."""
    api_key = current_app.config.get("ALPACA_API_KEY", "")
    api_secret = current_app.config.get("ALPACA_API_SECRET", "")
    paper = current_app.config.get("PAPER_TRADING", True)
    
    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set. Trading features will not work.")
        return None
    
    try:
        # Initialize trading client
        trading_client = TradingClient(api_key, api_secret, paper=paper)
        return trading_client
    except Exception as e:
        logger.error(f"Error initializing Alpaca Trading client: {str(e)}", exc_info=True)
        return None


def start_subscription_thread():
    """Start a background thread for Redis subscription."""
    global subscription_thread, is_running
    
    if subscription_thread and subscription_thread.is_alive():
        logger.info("Subscription thread already running")
        return
    
    is_running = True
    subscription_thread = threading.Thread(target=run_subscription_listener)
    subscription_thread.daemon = True
    subscription_thread.start()
    logger.info("Started subscription thread")


def run_subscription_listener():
    """Run the Redis subscription listener in a background thread."""
    global is_running
    
    # Get Redis client
    redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = RedisClient(redis_url)
    
    # Subscribe to channels
    pubsub = redis_client.subscribe([SIGNAL_TRIGGERED_CHANNEL])
    
    logger.info("Listening for Redis messages on execution channels...")
    
    while is_running:
        try:
            message = pubsub.get_message(timeout=1.0)
            if message and message['type'] == 'message':
                channel = message['channel'].decode('utf-8')
                data = json.loads(message['data'].decode('utf-8'))
                
                if channel == SIGNAL_TRIGGERED_CHANNEL:
                    handle_signal_triggered(data, redis_client)
            
            time.sleep(0.01)  # Short sleep to prevent CPU hogging
        except Exception as e:
            logger.error(f"Error in subscription thread: {str(e)}", exc_info=True)
            time.sleep(1)  # Longer sleep on error
    
    logger.info("Subscription thread stopped")


def handle_signal_triggered(data: Dict[str, Any], redis_client: RedisClient):
    """Handle a triggered signal by finding and executing an appropriate option trade."""
    try:
        symbol = data.get('symbol')
        category = data.get('category')
        signal_id = data.get('id')
        
        if not symbol or not category or not signal_id:
            logger.error(f"Invalid signal data: {data}")
            return
        
        # Determine trade direction
        direction = "bullish" if category in ["breakout", "bounce"] else "bearish"
        
        logger.info(f"Signal triggered: {symbol} {category} ({direction})")
        
        # Get option recommendation
        import requests
        response = requests.get(
            f"http://localhost:5000/api/options/recommend/{symbol}",
            params={"direction": direction, "signal_id": signal_id}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get option recommendation: {response.text}")
            return
        
        recommendation = response.json()
        if recommendation.get('status') != 'success':
            logger.error(f"Option recommendation error: {recommendation.get('message')}")
            return
        
        option = recommendation.get('recommendation')
        if not option:
            logger.error(f"No option recommendation found for {symbol} {direction}")
            return
        
        # Calculate position size based on risk parameters
        # For simplicity, we'll use a fixed position size of 1 contract
        quantity = 1
        
        # Create the order
        option_symbol = option.get('symbol')
        
        # Execute the trade
        execute_option_trade(option_symbol, direction, quantity, signal_id, redis_client)
        
    except Exception as e:
        logger.error(f"Error handling signal trigger: {str(e)}", exc_info=True)


def execute_option_trade(
    option_symbol: str,
    direction: str,
    quantity: int,
    signal_id: str,
    redis_client: RedisClient
):
    """Execute an option trade on Alpaca."""
    try:
        # Initialize trading client
        trading_client = initialize_trading_client()
        
        if not trading_client:
            logger.error("Trading client not initialized")
            return
        
        # Determine order side
        side = OrderSide.BUY if direction == "bullish" else OrderSide.SELL
        
        # Generate client order ID
        client_order_id = generate_client_order_id("aplus")
        
        # Create market order
        order_request = MarketOrderRequest(
            symbol=option_symbol,
            qty=quantity,
            side=side,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id
        )
        
        logger.info(f"Placing {side} order for {quantity} {option_symbol}")
        
        # Place the order
        order = trading_client.submit_order(order_request)
        
        # Create order data
        order_data = {
            "order_id": order.id,
            "client_order_id": client_order_id,
            "symbol": option_symbol,
            "quantity": quantity,
            "side": side.value,
            "type": "market",
            "status": order.status,
            "created_at": datetime.now().isoformat(),
            "signal_id": signal_id
        }
        
        # Publish order placed event
        redis_client.publish(ORDER_PLACED_CHANNEL, order_data)
        
        # Store order in Redis
        redis_client.set(f"order:{order.id}", order_data)
        
        logger.info(f"Order placed: {order.id}")
        
        return order_data
        
    except Exception as e:
        logger.error(f"Error executing option trade: {str(e)}", exc_info=True)
        return None


@execution_routes.route('/orders', methods=['GET'])
def get_orders():
    """Get all orders."""
    try:
        # Initialize trading client
        trading_client = initialize_trading_client()
        
        if not trading_client:
            return jsonify({"status": "error", "message": "Trading client not initialized"}), 500
        
        # Get query parameters
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        # Get orders from Alpaca - using list_orders() instead of get_orders() with updated parameters
        try:
            from alpaca.trading.requests import GetOrdersRequest
            # For newer versions of alpaca-py
            params = {"limit": limit}
            if status:
                params["status"] = status
            orders = trading_client.get_orders(**params)
        except (TypeError, AttributeError):
            # Fall back to list_orders() for compatibility
            if status:
                orders = trading_client.list_orders(status=status, limit=limit)
            else:
                orders = trading_client.list_orders(limit=limit)
        
        # Format response
        formatted_orders = []
        for order in orders:
            formatted_orders.append({
                "id": order.id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "quantity": order.qty,
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status,
                "filled_quantity": order.filled_qty,
                "filled_price": order.filled_avg_price,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None
            })
        
        return jsonify({
            "status": "success",
            "count": len(formatted_orders),
            "orders": formatted_orders
        })
        
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get a specific order by ID."""
    try:
        # Initialize trading client
        trading_client = initialize_trading_client()
        
        if not trading_client:
            return jsonify({"status": "error", "message": "Trading client not initialized"}), 500
        
        # Get order from Alpaca
        order = trading_client.get_order_by_id(order_id)
        
        # Format response
        formatted_order = {
            "id": order.id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "quantity": order.qty,
            "side": order.side.value,
            "type": order.type.value,
            "status": order.status,
            "filled_quantity": order.filled_qty,
            "filled_price": order.filled_avg_price,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None
        }
        
        return jsonify({
            "status": "success",
            "order": formatted_order
        })
        
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/positions', methods=['GET'])
def get_positions():
    """Get all positions."""
    try:
        # Initialize trading client
        trading_client = initialize_trading_client()
        
        if not trading_client:
            return jsonify({"status": "error", "message": "Trading client not initialized"}), 500
        
        # Get positions from Alpaca
        positions = trading_client.get_all_positions()
        
        # Format response
        formatted_positions = []
        for position in positions:
            formatted_positions.append({
                "symbol": position.symbol,
                "quantity": position.qty,
                "side": "long" if float(position.qty) > 0 else "short",
                "avg_entry_price": position.avg_entry_price,
                "market_value": position.market_value,
                "cost_basis": position.cost_basis,
                "unrealized_pl": position.unrealized_pl,
                "unrealized_plpc": position.unrealized_plpc,
                "current_price": position.current_price,
                "lastday_price": position.lastday_price,
                "change_today": position.change_today
            })
        
        return jsonify({
            "status": "success",
            "count": len(formatted_positions),
            "positions": formatted_positions
        })
        
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/positions/<symbol>', methods=['GET'])
def get_position(symbol):
    """Get a specific position by symbol."""
    try:
        # Initialize trading client
        trading_client = initialize_trading_client()
        
        if not trading_client:
            return jsonify({"status": "error", "message": "Trading client not initialized"}), 500
        
        # Get position from Alpaca
        position = trading_client.get_open_position(symbol)
        
        # Format response
        formatted_position = {
            "symbol": position.symbol,
            "quantity": position.qty,
            "side": "long" if float(position.qty) > 0 else "short",
            "avg_entry_price": position.avg_entry_price,
            "market_value": position.market_value,
            "cost_basis": position.cost_basis,
            "unrealized_pl": position.unrealized_pl,
            "unrealized_plpc": position.unrealized_plpc,
            "current_price": position.current_price,
            "lastday_price": position.lastday_price,
            "change_today": position.change_today
        }
        
        return jsonify({
            "status": "success",
            "position": formatted_position
        })
        
    except Exception as e:
        logger.error(f"Error getting position for {symbol}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/trade', methods=['POST'])
def manual_trade():
    """Place a manual trade."""
    try:
        # Get Redis client
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = RedisClient(redis_url)
        
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        symbol = data.get('symbol')
        direction = data.get('direction', 'bullish')
        quantity = int(data.get('quantity', 1))
        order_type = data.get('order_type', 'market').lower()
        
        if not symbol:
            return jsonify({"status": "error", "message": "Symbol is required"}), 400
        
        if direction not in ['bullish', 'bearish']:
            return jsonify({"status": "error", "message": "Direction must be 'bullish' or 'bearish'"}), 400
        
        if order_type not in ['market', 'limit', 'stop']:
            return jsonify({"status": "error", "message": "Order type must be 'market', 'limit', or 'stop'"}), 400
        
        # If this is a direct option symbol
        if '_' in symbol and ('C' in symbol or 'P' in symbol):
            option_symbol = symbol
        else:
            # Get option recommendation
            import requests
            response = requests.get(
                f"http://localhost:5000/api/options/recommend/{symbol}",
                params={"direction": direction}
            )
            
            if response.status_code != 200:
                return jsonify({
                    "status": "error", 
                    "message": f"Failed to get option recommendation: {response.text}"
                }), 500
            
            recommendation = response.json()
            if recommendation.get('status') != 'success':
                return jsonify({
                    "status": "error", 
                    "message": f"Option recommendation error: {recommendation.get('message')}"
                }), 500
            
            option = recommendation.get('recommendation')
            if not option:
                return jsonify({
                    "status": "error", 
                    "message": f"No option recommendation found for {symbol} {direction}"
                }), 404
            
            option_symbol = option.get('symbol')
        
        # Create client_order_id
        client_id = data.get('client_id', generate_client_order_id("manual"))
        
        # Execute the trade
        trade_result = execute_option_trade(option_symbol, direction, quantity, client_id, redis_client)
        
        if not trade_result:
            return jsonify({"status": "error", "message": "Failed to execute trade"}), 500
        
        return jsonify({
            "status": "success",
            "message": f"Trade executed: {direction} {quantity} {option_symbol}",
            "order": trade_result
        })
        
    except Exception as e:
        logger.error(f"Error executing manual trade: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/close/<symbol>', methods=['POST'])
def close_position(symbol):
    """Close a specific position."""
    try:
        # Initialize trading client
        trading_client = initialize_trading_client()
        
        if not trading_client:
            return jsonify({"status": "error", "message": "Trading client not initialized"}), 500
        
        # Close the position
        response = trading_client.close_position(symbol)
        
        # Format response
        result = {
            "symbol": symbol,
            "status": "closed",
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify({
            "status": "success",
            "message": f"Position {symbol} closed",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error closing position {symbol}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/start', methods=['POST'])
def start_executor():
    """Start the execution service."""
    try:
        start_subscription_thread()
        
        return jsonify({
            "status": "success",
            "message": "Execution service started"
        })
        
    except Exception as e:
        logger.error(f"Error starting execution service: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/stop', methods=['POST'])
def stop_executor():
    """Stop the execution service."""
    global is_running
    
    try:
        is_running = False
        
        return jsonify({
            "status": "success",
            "message": "Execution service stopping"
        })
        
    except Exception as e:
        logger.error(f"Error stopping execution service: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@execution_routes.route('/status', methods=['GET'])
def executor_status():
    """Get the status of the execution service."""
    global is_running, subscription_thread
    
    thread_alive = subscription_thread is not None and subscription_thread.is_alive()
    
    return jsonify({
        "status": "success",
        "executor": {
            "running": is_running and thread_alive,
        }
    })
