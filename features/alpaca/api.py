"""
Alpaca API Module

This module provides the Flask API routes for interacting with
Alpaca trading functionality.
"""
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app

from common.db import db
from features.alpaca.client import (
    initialize_clients, get_account_info, get_positions, 
    get_open_orders, get_latest_quote
)
from features.alpaca.signal_processor import process_signal
from features.setups.models import Signal, TickerSetup, SetupMessage

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
alpaca_bp = Blueprint('alpaca', __name__, url_prefix='/api/v1/trading')

def register_routes(app):
    """Register Alpaca API routes with the Flask app."""
    app.register_blueprint(alpaca_bp)
    logger.info("Alpaca API routes registered")
    
    # Initialize Alpaca clients on app start
    with app.app_context():
        initialized = initialize_clients()
        if initialized:
            logger.info("Alpaca clients initialized successfully")
        else:
            logger.warning("Failed to initialize Alpaca clients")

@alpaca_bp.route('/account', methods=['GET'])
def get_account():
    """
    Get Alpaca account information.
    
    Returns:
        JSON with account information
    """
    account = get_account_info()
    if not account:
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve account information'
        }), 500
    
    return jsonify({
        'status': 'success',
        'account': account
    })

@alpaca_bp.route('/positions', methods=['GET'])
def get_current_positions():
    """
    Get current positions.
    
    Returns:
        JSON with positions
    """
    positions = get_positions()
    
    return jsonify({
        'status': 'success',
        'positions': positions
    })

@alpaca_bp.route('/orders', methods=['GET'])
def get_current_orders():
    """
    Get open orders.
    
    Returns:
        JSON with orders
    """
    orders = get_open_orders()
    
    return jsonify({
        'status': 'success',
        'orders': orders
    })

@alpaca_bp.route('/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """
    Get latest quote for a symbol.
    
    Args:
        symbol: Ticker symbol
        
    Returns:
        JSON with quote information
    """
    quote = get_latest_quote(symbol)
    if not quote:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve quote for {symbol}'
        }), 404
    
    return jsonify({
        'status': 'success',
        'quote': quote
    })

@alpaca_bp.route('/signals', methods=['GET'])
def get_active_signals():
    """
    Get active trading signals.
    
    Query parameters:
    - limit: Maximum number of signals to return (default: 10)
    
    Returns:
        JSON with active signals
    """
    try:
        limit = int(request.args.get('limit', 10))
        
        # Query active signals, ordered by creation date
        signals = Signal.query.filter_by(active=True)\
                            .order_by(Signal.created_at.desc())\
                            .limit(limit)\
                            .all()
        
        # Format response
        signal_data = []
        for signal in signals:
            ticker_setup = signal.ticker_setup
            signal_data.append({
                'id': signal.id,
                'symbol': ticker_setup.symbol,
                'category': signal.category.value,
                'comparison': signal.comparison.value,
                'trigger': signal.trigger,
                'created_at': signal.created_at.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'signals': signal_data
        })
    except Exception as e:
        logger.error(f"Error getting active signals: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting active signals: {str(e)}'
        }), 500

@alpaca_bp.route('/signals/process/<int:signal_id>', methods=['POST'])
def process_single_signal(signal_id):
    """
    Process a single trading signal.
    
    Args:
        signal_id: ID of the signal to process
        
    JSON parameters:
    - test_mode: Whether to run in test mode (default: true)
    
    Returns:
        JSON with processing results
    """
    try:
        # Get JSON parameters
        data = request.get_json() or {}
        test_mode = data.get('test_mode', True)
        
        # Check if signal exists
        signal = Signal.query.get(signal_id)
        if not signal:
            return jsonify({
                'status': 'error',
                'message': f'Signal not found: {signal_id}'
            }), 404
        
        # Process the signal
        result = process_signal(signal_id, test_mode)
        
        return jsonify({
            'status': 'success',
            'result': result
        })
    except Exception as e:
        logger.error(f"Error processing signal {signal_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing signal: {str(e)}'
        }), 500

@alpaca_bp.route('/signals/process/latest', methods=['POST'])
def process_latest_signals():
    """
    Process the latest active signals.
    
    JSON parameters:
    - limit: Maximum number of signals to process (default: 5)
    - test_mode: Whether to run in test mode (default: true)
    
    Returns:
        JSON with processing results
    """
    try:
        # Get JSON parameters
        data = request.get_json() or {}
        limit = data.get('limit', 5)
        test_mode = data.get('test_mode', True)
        
        # Query latest active signals
        signals = Signal.query.filter_by(active=True)\
                            .order_by(Signal.created_at.desc())\
                            .limit(limit)\
                            .all()
        
        # Process each signal
        results = []
        for signal in signals:
            result = process_signal(signal.id, test_mode)
            results.append({
                'signal_id': signal.id,
                'symbol': signal.ticker_setup.symbol,
                'result': result
            })
        
        return jsonify({
            'status': 'success',
            'processed_count': len(results),
            'results': results
        })
    except Exception as e:
        logger.error(f"Error processing latest signals: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing latest signals: {str(e)}'
        }), 500