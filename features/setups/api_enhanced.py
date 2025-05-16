"""
Enhanced API Routes for Trading Setups

This module provides enhanced API routes for handling trading setup messages,
including support for multi-ticker messages.
"""
import logging
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from typing import Dict, List, Any, Optional

from app import app
from common.models import TradeSetupMessage, TickerSetup as DTOTickerSetup
from features.setups.parser import SetupParser
from features.setups.setup_service import SetupService
from features.rate_limiter import configure_rate_limits

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "20 per hour"]
)

# Create blueprint
setup_enhanced_bp = Blueprint('setup_enhanced', __name__, url_prefix='/api/v1/setups')

# Configure setup parser
parser = SetupParser()

# Configure logger
logger = logging.getLogger(__name__)

def register_routes(app):
    """Register enhanced setup routes with the Flask app."""
    app.register_blueprint(setup_enhanced_bp)
    logger.info("Enhanced setup routes registered")

# API routes
@setup_enhanced_bp.route('/webhook', methods=['POST'])
@configure_rate_limits(limiter, ["50 per day", "10 per hour"])
def receive_setup_webhook():
    """
    Receive a setup message from a webhook.
    
    Expects JSON payload with:
    - text: The raw setup message text
    - date: (Optional) Date of the setup message (YYYY-MM-DD), defaults to today
    - source: (Optional) Source of the message, defaults to 'webhook'
    
    Returns:
    - JSON with parsed ticker setups and status
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        if 'text' not in data or not data['text']:
            return jsonify({'error': 'Missing required field: text'}), 400
        
        # Extract data
        text = data.get('text', '').strip()
        source = data.get('source', 'webhook')
        
        # Handle date
        try:
            if 'date' in data and data['date']:
                setup_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            else:
                setup_date = datetime.now().date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Parse the setup message
        setup_message = parser.parse_message(text, date=setup_date, source=source)
        
        # Check if parsing was successful
        if not setup_message or not setup_message.setups:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse any ticker setups from the message',
                'raw_text': text
            }), 400
        
        # Save to database
        setup_id = SetupService.save_setup(setup_message)
        
        if not setup_id:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save the setup message to the database',
                'parsed': setup_message_to_dict(setup_message)
            }), 500
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Setup message successfully processed',
            'setup_id': setup_id,
            'parsed': setup_message_to_dict(setup_message)
        }), 201
        
    except Exception as e:
        logger.error(f"Error processing setup webhook: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'An error occurred while processing the webhook: {str(e)}'
        }), 500

@setup_enhanced_bp.route('/<int:setup_id>', methods=['GET'])
def get_setup(setup_id: int):
    """
    Get a setup message by ID.
    
    Args:
        setup_id: The ID of the setup message
        
    Returns:
        JSON response with setup message data
    """
    setup = SetupService.get_setup_by_id(setup_id)
    
    if not setup:
        return jsonify({
            'status': 'error',
            'message': f'Setup with ID {setup_id} not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': setup
    }), 200

@setup_enhanced_bp.route('/recent', methods=['GET'])
def get_recent_setups():
    """
    Get recent setup messages.
    
    Query parameters:
    - limit: Maximum number of setups to return (default: 10)
    - symbol: (Optional) Filter by ticker symbol
    
    Returns:
        JSON response with recent setup messages
    """
    limit = request.args.get('limit', default=10, type=int)
    symbol = request.args.get('symbol', default=None, type=str)
    
    if limit <= 0 or limit > 100:
        return jsonify({
            'status': 'error',
            'message': 'Limit must be between 1 and 100'
        }), 400
    
    setups = SetupService.get_recent_setups(limit=limit, symbol=symbol)
    
    return jsonify({
        'status': 'success',
        'data': setups
    }), 200

@setup_enhanced_bp.route('/symbol/<symbol>', methods=['GET'])
def get_setups_by_symbol(symbol: str):
    """
    Get setup messages for a specific ticker symbol.
    
    Args:
        symbol: Ticker symbol to filter by
        
    Query parameters:
    - limit: Maximum number of setups to return (default: 10)
    
    Returns:
        JSON response with ticker setups for the specified symbol
    """
    limit = request.args.get('limit', default=10, type=int)
    
    if limit <= 0 or limit > 100:
        return jsonify({
            'status': 'error',
            'message': 'Limit must be between 1 and 100'
        }), 400
    
    setups = SetupService.get_setups_by_symbol(symbol=symbol, limit=limit)
    
    return jsonify({
        'status': 'success',
        'data': setups
    }), 200

# Helper functions
def setup_message_to_dict(message: TradeSetupMessage) -> Dict[str, Any]:
    """
    Convert a TradeSetupMessage to a dictionary for JSON response.
    
    Args:
        message: The setup message object
        
    Returns:
        Dict representation of the setup message
    """
    return {
        'date': message.date.isoformat() if message.date else None,
        'source': message.source,
        'ticker_count': len(message.setups),
        'tickers': [ticker_setup_to_dict(setup) for setup in message.setups]
    }

def ticker_setup_to_dict(setup: DTOTickerSetup) -> Dict[str, Any]:
    """
    Convert a TickerSetup to a dictionary for JSON response.
    
    Args:
        setup: The ticker setup object
        
    Returns:
        Dict representation of the ticker setup
    """
    return {
        'symbol': setup.symbol,
        'signals': [
            {
                'category': signal.category.value,
                'comparison': signal.comparison.value,
                'trigger': signal.trigger,
                'targets': list(signal.targets),
                'aggressiveness': signal.aggressiveness.value
            }
            for signal in setup.signals
        ],
        'bias': bias_to_dict(setup.bias) if setup.bias else None
    }

def bias_to_dict(bias) -> Optional[Dict[str, Any]]:
    """
    Convert a Bias to a dictionary for JSON response.
    
    Args:
        bias: The bias object
        
    Returns:
        Dict representation of the bias
    """
    if not bias:
        return None
    
    result = {
        'direction': bias.direction.value,
        'condition': bias.condition.value,
        'price': bias.price,
        'flip': None
    }
    
    if bias.flip:
        result['flip'] = {
            'direction': bias.flip.direction.value,
            'price_level': bias.flip.price_level
        }
    
    return result