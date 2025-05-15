import logging
import json
from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from common.models import TradeSetupMessage, TickerSetup
from features.setups.parser import SetupParser
from common.redis_utils import RedisClient

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint
setup_routes = Blueprint('setups', __name__, url_prefix='/api/setups')

# Initialize parser
parser = SetupParser()

# Redis channels
SETUP_CHANNEL = "aplus.setups"


@setup_routes.route('/webhook', methods=['POST'])
def receive_webhook():
    """
    Endpoint to receive A+ Setup messages from Discord/Email webhook.
    Parses the raw message and publishes the parsed setup to Redis.
    """
    try:
        # Get Redis client from app
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = RedisClient(redis_url)
        
        # Extract data from request
        data = request.json
        
        # Check if 'content' field exists (Discord format)
        if 'content' in data:
            raw_text = data['content']
            source = "discord"
        # Email webhook format
        elif 'body' in data:
            raw_text = data['body']
            source = "email"
        else:
            raw_text = request.data.decode('utf-8')
            source = "unknown"
        
        logger.debug(f"Received webhook data from {source}: {raw_text[:100]}...")
        
        # Parse the setup
        parsed_setups = parser.parse_raw_setup(raw_text)
        
        if not parsed_setups:
            return jsonify({"status": "error", "message": "Failed to parse setup"}), 400
        
        # Create a TradeSetupMessage
        setup_message = TradeSetupMessage(
            date=date.today(),
            raw_text=raw_text,
            setups=parsed_setups,
            source=source,
            created_at=datetime.now()
        )
        
        # Store in Redis
        message_key = f"setup:{setup_message.created_at.isoformat()}"
        redis_client.set(message_key, setup_message.dict())
        
        # Publish to Redis channel
        redis_client.publish(SETUP_CHANNEL, setup_message.dict())
        
        # Return success response
        return jsonify({
            "status": "success",
            "message": "Setup received and processed",
            "setup_id": message_key,
            "tickers": [setup.symbol for setup in parsed_setups]
        })
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@setup_routes.route('/', methods=['GET'])
def get_setups():
    """
    Get all stored setup messages.
    """
    try:
        # Get Redis client from app
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = RedisClient(redis_url)
        
        # Get all keys matching the setup pattern
        setup_keys = redis_client.redis.keys("setup:*")
        
        # Initialize result list
        setups = []
        
        # Get all setup values
        for key in setup_keys:
            setup_data = redis_client.get(key.decode('utf-8'), as_json=True)
            if setup_data:
                setups.append(setup_data)
        
        # Sort by created_at timestamp (descending)
        setups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            "status": "success",
            "count": len(setups),
            "setups": setups
        })
        
    except Exception as e:
        logger.error(f"Error retrieving setups: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@setup_routes.route('/<ticker>', methods=['GET'])
def get_ticker_setups(ticker):
    """
    Get setups for a specific ticker.
    """
    try:
        # Get Redis client from app
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = RedisClient(redis_url)
        
        # Get all keys matching the setup pattern
        setup_keys = redis_client.redis.keys("setup:*")
        
        # Initialize result list
        ticker_setups = []
        
        # Get all setup values and filter by ticker
        for key in setup_keys:
            setup_data = redis_client.get(key.decode('utf-8'), as_json=True)
            if setup_data and 'setups' in setup_data:
                for setup in setup_data['setups']:
                    if setup.get('symbol', '').upper() == ticker.upper():
                        ticker_setups.append({
                            "setup_id": key.decode('utf-8'),
                            "created_at": setup_data.get('created_at'),
                            "ticker_setup": setup
                        })
        
        # Sort by created_at timestamp (descending)
        ticker_setups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            "status": "success",
            "ticker": ticker.upper(),
            "count": len(ticker_setups),
            "setups": ticker_setups
        })
        
    except Exception as e:
        logger.error(f"Error retrieving setups for ticker {ticker}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@setup_routes.route('/manual', methods=['POST'])
def manual_setup():
    """
    Endpoint to manually input a setup message.
    """
    try:
        # Get Redis client from app
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = RedisClient(redis_url)
        
        # Extract data from request
        data = request.json
        
        if not data or 'raw_text' not in data:
            return jsonify({"status": "error", "message": "Missing raw_text field"}), 400
        
        raw_text = data['raw_text']
        
        # Parse the setup
        parsed_setups = parser.parse_raw_setup(raw_text)
        
        if not parsed_setups:
            return jsonify({"status": "error", "message": "Failed to parse setup"}), 400
        
        # Create a TradeSetupMessage
        setup_message = TradeSetupMessage(
            date=date.today(),
            raw_text=raw_text,
            setups=parsed_setups,
            source="manual",
            created_at=datetime.now()
        )
        
        # Store in Redis
        message_key = f"setup:{setup_message.created_at.isoformat()}"
        redis_client.set(message_key, setup_message.dict())
        
        # Publish to Redis channel
        redis_client.publish(SETUP_CHANNEL, setup_message.dict())
        
        # Return success response
        return jsonify({
            "status": "success",
            "message": "Setup received and processed",
            "setup_id": message_key,
            "tickers": [setup.symbol for setup in parsed_setups]
        })
        
    except Exception as e:
        logger.error(f"Error processing manual setup: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
