import logging
import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request, current_app
from common.models import Signal, TickerSetup, BiasDirection, ComparisonType, SignalCategory
from common.redis_utils import RedisClient

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint
strategy_routes = Blueprint('strategy', __name__, url_prefix='/api/strategy')

# Redis channels
SETUP_CHANNEL = "aplus.setups"
PRICE_UPDATE_CHANNEL = "aplus.market.price_update"
TRIGGER_CHANNEL = "aplus.market.trigger"
SIGNAL_TRIGGERED_CHANNEL = "aplus.strategy.signal_triggered"

# Store active signals
active_signals: Dict[str, List[Dict[str, Any]]] = {}

# Background thread for subscription
subscription_thread = None
is_running = False


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
    pubsub = redis_client.subscribe([SETUP_CHANNEL, PRICE_UPDATE_CHANNEL, TRIGGER_CHANNEL])
    
    logger.info("Listening for Redis messages on strategy channels...")
    
    while is_running:
        try:
            message = pubsub.get_message(timeout=1.0)
            if message and message['type'] == 'message':
                channel = message['channel'].decode('utf-8')
                data = json.loads(message['data'].decode('utf-8'))
                
                if channel == SETUP_CHANNEL:
                    handle_setup_message(data, redis_client)
                elif channel == PRICE_UPDATE_CHANNEL:
                    handle_price_update(data, redis_client)
                elif channel == TRIGGER_CHANNEL:
                    handle_trigger_event(data, redis_client)
            
            time.sleep(0.01)  # Short sleep to prevent CPU hogging
        except Exception as e:
            logger.error(f"Error in subscription thread: {str(e)}", exc_info=True)
            time.sleep(1)  # Longer sleep on error
    
    logger.info("Subscription thread stopped")


def handle_setup_message(data: Dict[str, Any], redis_client: RedisClient):
    """Handle an incoming setup message."""
    global active_signals
    
    if 'setups' not in data:
        return
    
    # Process each ticker setup
    for setup in data['setups']:
        symbol = setup.get('symbol')
        if not symbol:
            continue
        
        signals = setup.get('signals', [])
        
        # Initialize active signals for this symbol if not exists
        if symbol not in active_signals:
            active_signals[symbol] = []
        
        # Add each signal to active signals
        for signal in signals:
            try:
                # Create new active signal entry
                active_signal = {
                    'symbol': symbol,
                    'category': signal.get('category'),
                    'comparison': signal.get('comparison'),
                    'trigger': signal.get('trigger'),
                    'targets': signal.get('targets', []),
                    'aggressiveness': signal.get('aggressiveness', 'none'),
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                    'id': f"signal_{symbol}_{datetime.now().timestamp()}"
                }
                
                # Add to active signals
                active_signals[symbol].append(active_signal)
                
                # Register price trigger
                trigger_data = {
                    'symbol': symbol,
                    'comparison': active_signal['comparison'],
                    'price': active_signal['trigger'],
                    'id': active_signal['id']
                }
                
                # Make API request to register trigger
                import requests
                response = requests.post(
                    'http://localhost:5000/api/market/triggers',
                    json=trigger_data
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to register price trigger: {response.text}")
                
                logger.info(f"Registered signal for {symbol}: {active_signal['category']} {active_signal['comparison']} {active_signal['trigger']}")
                
            except Exception as e:
                logger.error(f"Error registering signal: {str(e)}", exc_info=True)


def handle_price_update(data: Dict[str, Any], redis_client: RedisClient):
    """Handle a price update."""
    # This method can be expanded later if we need to do something with every price update
    pass


def handle_trigger_event(data: Dict[str, Any], redis_client: RedisClient):
    """Handle a price trigger event."""
    global active_signals
    
    symbol = data.get('symbol')
    trigger_id = data.get('trigger_id')
    current_price = data.get('price')
    
    if not symbol or not trigger_id or symbol not in active_signals:
        return
    
    # Find the matching signal
    matched_signal = None
    for signal in active_signals[symbol]:
        if signal.get('id') == trigger_id:
            matched_signal = signal
            break
    
    if not matched_signal:
        return
    
    # Update signal status
    matched_signal['status'] = 'triggered'
    matched_signal['trigger_price'] = current_price
    matched_signal['triggered_at'] = datetime.now().isoformat()
    
    # Publish signal triggered event
    redis_client.publish(SIGNAL_TRIGGERED_CHANNEL, matched_signal)
    
    logger.info(f"Signal triggered: {symbol} {matched_signal['category']} at {current_price}")


@strategy_routes.route('/signals', methods=['GET'])
def get_signals():
    """Get all active signals."""
    global active_signals
    
    symbol = request.args.get('symbol')
    status = request.args.get('status')
    
    result = {}
    
    for sym, signals in active_signals.items():
        # Filter by symbol if specified
        if symbol and sym.upper() != symbol.upper():
            continue
        
        # Filter signals by status if specified
        if status:
            filtered_signals = [s for s in signals if s.get('status') == status]
        else:
            filtered_signals = signals
        
        if filtered_signals:
            result[sym] = filtered_signals
    
    return jsonify({
        "status": "success",
        "count": sum(len(signals) for signals in result.values()),
        "signals": result
    })


@strategy_routes.route('/signals/<signal_id>', methods=['GET'])
def get_signal(signal_id):
    """Get a specific signal by ID."""
    global active_signals
    
    for symbol, signals in active_signals.items():
        for signal in signals:
            if signal.get('id') == signal_id:
                return jsonify({
                    "status": "success",
                    "signal": signal
                })
    
    return jsonify({
        "status": "error",
        "message": f"Signal with ID {signal_id} not found"
    }), 404


@strategy_routes.route('/signals/<signal_id>', methods=['DELETE'])
def delete_signal(signal_id):
    """Delete a specific signal by ID."""
    global active_signals
    
    for symbol, signals in active_signals.items():
        for i, signal in enumerate(signals):
            if signal.get('id') == signal_id:
                active_signals[symbol].pop(i)
                return jsonify({
                    "status": "success",
                    "message": f"Signal {signal_id} deleted"
                })
    
    return jsonify({
        "status": "error",
        "message": f"Signal with ID {signal_id} not found"
    }), 404


@strategy_routes.route('/start', methods=['POST'])
def start_detector():
    """Start the strategy detector."""
    try:
        start_subscription_thread()
        
        return jsonify({
            "status": "success",
            "message": "Strategy detector started"
        })
        
    except Exception as e:
        logger.error(f"Error starting strategy detector: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@strategy_routes.route('/stop', methods=['POST'])
def stop_detector():
    """Stop the strategy detector."""
    global is_running
    
    try:
        is_running = False
        
        return jsonify({
            "status": "success",
            "message": "Strategy detector stopping"
        })
        
    except Exception as e:
        logger.error(f"Error stopping strategy detector: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@strategy_routes.route('/status', methods=['GET'])
def detector_status():
    """Get the status of the strategy detector."""
    global is_running, subscription_thread
    
    thread_alive = subscription_thread is not None and subscription_thread.is_alive()
    
    return jsonify({
        "status": "success",
        "detector": {
            "running": is_running and thread_alive,
            "active_symbols": len(active_signals),
            "active_signals": sum(len(signals) for signals in active_signals.values())
        }
    })
