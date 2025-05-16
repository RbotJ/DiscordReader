"""
Enhanced Setups API Module (Adapter Pattern)

This module provides improved endpoints for receiving trading setup messages
and storing them in the database using the adapter pattern.
"""
import logging
import json
from flask import Blueprint, request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from features.setups.service_adapter import SetupServiceAdapter
from features.setups.auth import require_auth
from common.models import TradeSetupMessage

logger = logging.getLogger(__name__)
adapter_setups_blueprint = Blueprint('adapter_setups', __name__)

# Configure rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@adapter_setups_blueprint.route('/api/v2/setups/webhook', methods=['POST'])
@limiter.limit("20 per minute")
@require_auth
def setup_webhook():
    """
    Enhanced endpoint for receiving trading setup webhook messages.
    
    Accepts webhook POST requests with raw text messages.
    Parses the message and stores in the database using our adapter.
    Requires valid authentication signature in headers.
    Implements rate limiting to prevent abuse.
    
    Returns:
        JSON response with status
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Request must be JSON',
            'code': 'INVALID_FORMAT'
        }), 400
    
    data = request.get_json()
    
    # Get signature from headers if present
    signature = request.headers.get('X-Webhook-Signature')
    
    # Process the webhook
    success, response = SetupServiceAdapter.process_webhook(data, signature)
    
    if success:
        return jsonify(response), 201
    else:
        return jsonify(response), 400


@adapter_setups_blueprint.route('/api/v2/setups/parse', methods=['POST'])
@limiter.limit("30 per minute")
def parse_setup():
    """
    Enhanced endpoint for parsing a setup message without storing it.
    
    Useful for testing/validating setup messages.
    Implements rate limiting to prevent abuse.
    
    Returns:
        JSON response with parsed data
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Request must be JSON',
            'code': 'INVALID_FORMAT'
        }), 400
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required field: text',
            'code': 'MISSING_FIELD'
        }), 400
    
    try:
        # Use the service to process the message without saving
        from features.setups.parser import parse_setup_message
        
        # Parse the message
        source = data.get('source', 'test')
        setup_message = parse_setup_message(data['text'], source)
        
        # Prepare response with ticker details
        ticker_details = []
        for setup in setup_message.setups:
            ticker_detail = {
                'symbol': setup.symbol,
                'signals': [s.dict() for s in setup.signals],
                'bias': setup.bias.dict() if setup.bias else None
            }
            ticker_details.append(ticker_detail)
        
        return jsonify({
            'success': True,
            'date': setup_message.date.isoformat() if setup_message.date else None,
            'tickers': [setup.symbol for setup in setup_message.setups],
            'ticker_count': len(setup_message.setups),
            'ticker_details': ticker_details
        }), 200
        
    except Exception as e:
        logger.exception(f"Error parsing setup message: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error parsing the message: {str(e)}',
            'code': 'PARSING_ERROR'
        }), 500


@adapter_setups_blueprint.route('/api/v2/setups', methods=['GET'])
def get_setups():
    """
    Get recent setup messages.
    
    Optional query parameters:
    - limit: Maximum number of setups to retrieve (default: 10)
    
    Returns:
        JSON response with setups data
    """
    try:
        # Get limit parameter with default
        limit = request.args.get('limit', default=10, type=int)
        
        # Get setups from repository
        setups = SetupServiceAdapter.get_recent_setups(limit)
        
        # Prepare response
        result = []
        for setup in setups:
            setup_data = {
                'date': setup.date.isoformat(),
                'source': setup.source,
                'created_at': setup.created_at.isoformat(),
                'ticker_count': len(setup.setups),
                'tickers': [t.symbol for t in setup.setups]
            }
            result.append(setup_data)
        
        return jsonify({
            'success': True,
            'setups': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving setups: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error retrieving setups: {str(e)}',
            'code': 'RETRIEVAL_ERROR'
        }), 500


@adapter_setups_blueprint.route('/api/v2/setups/symbol/<symbol>', methods=['GET'])
def get_setups_by_symbol(symbol):
    """
    Get trade setups for a specific ticker symbol.
    
    Args:
        symbol: The ticker symbol to retrieve setups for
        
    Optional query parameters:
    - limit: Maximum number of setups to retrieve (default: 10)
    
    Returns:
        JSON response with setup data for the symbol
    """
    try:
        # Validate symbol
        if not symbol or len(symbol) > 10:
            return jsonify({
                'success': False,
                'error': 'Invalid symbol',
                'code': 'INVALID_SYMBOL'
            }), 400
        
        # Get limit parameter with default
        limit = request.args.get('limit', default=10, type=int)
        
        # Get setups for symbol
        setups = SetupServiceAdapter.get_setups_for_symbol(symbol.upper(), limit)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'setups': setups,
            'count': len(setups)
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving setups for symbol {symbol}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error retrieving setups: {str(e)}',
            'code': 'RETRIEVAL_ERROR'
        }), 500


def register_routes(app):
    """Register adapter setup routes with the Flask app."""
    app.register_blueprint(adapter_setups_blueprint)
    
    # Apply limiter to the app
    limiter.init_app(app)
    
    logger.info("Adapter setup routes registered")