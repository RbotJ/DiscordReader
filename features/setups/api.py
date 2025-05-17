"""
Trading Setup API Module

This module provides API endpoints for retrieving trading setup data.
"""
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from models import SetupMessage, TickerSetup

logger = logging.getLogger(__name__)

# Create blueprint for setup API
setups_bp = Blueprint('setups', __name__, url_prefix='/api/setups')

@setups_bp.route('/recent', methods=['GET'])
def get_recent_setups():
    """
    Get recent setup messages.
    
    Query parameters:
    - limit: Maximum number of setups to return (default: 10)
    - symbol: Filter by ticker symbol (optional)
    
    Returns:
        JSON response with recent setup messages
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=10, type=int)
        symbol = request.args.get('symbol', default=None, type=str)
        
        # Validate limit
        if limit <= 0 or limit > 100:
            return jsonify({
                'status': 'error',
                'message': 'Limit must be between 1 and 100'
            }), 400
        
        # Build query
        query = SetupMessage.query.order_by(SetupMessage.created_at.desc())
        
        # Add symbol filter if provided
        if symbol:
            query = query.join(SetupMessage.ticker_setups).filter(TickerSetup.symbol == symbol)
        
        # Get limited results
        messages = query.limit(limit).all()
        
        # Convert to response format
        result = []
        for message in messages:
            message_data = {
                'id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'source': message.source,
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'ticker_count': len(message.ticker_setups),
                'ticker_symbols': [ts.symbol for ts in message.ticker_setups]
            }
            result.append(message_data)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent setups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting recent setups: {str(e)}'
        }), 500

@setups_bp.route('/<int:setup_id>', methods=['GET'])
def get_setup(setup_id):
    """
    Get a setup message by ID.
    
    Args:
        setup_id: The ID of the setup message
        
    Returns:
        JSON response with setup message data
    """
    try:
        # Get setup message by ID
        setup = SetupMessage.query.get(setup_id)
        
        if not setup:
            return jsonify({
                'status': 'error',
                'message': f'Setup with ID {setup_id} not found'
            }), 404
        
        # Convert to response format
        setup_data = {
            'id': setup.id,
            'date': setup.date.isoformat() if setup.date else None,
            'source': setup.source,
            'created_at': setup.created_at.isoformat() if setup.created_at else None,
            'raw_text': setup.raw_text,
            'ticker_setups': []
        }
        
        # Add ticker setups
        for ts in setup.ticker_setups:
            ticker_setup = {
                'id': ts.id,
                'symbol': ts.symbol,
                'text': ts.text,
                'signals': [],
                'bias': None
            }
            
            # Add signals
            for signal in ts.signals:
                signal_data = {
                    'id': signal.id,
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': signal.targets
                }
                ticker_setup['signals'].append(signal_data)
            
            # Add bias if present
            if ts.bias:
                bias_data = {
                    'id': ts.bias.id,
                    'direction': ts.bias.direction.value,
                    'condition': ts.bias.condition.value,
                    'price': ts.bias.price,
                    'flip': None
                }
                
                # Add bias flip if present
                if ts.bias.bias_flip:
                    bias_data['flip'] = {
                        'id': ts.bias.bias_flip.id,
                        'direction': ts.bias.bias_flip.direction.value,
                        'price_level': ts.bias.bias_flip.price_level
                    }
                
                ticker_setup['bias'] = bias_data
            
            setup_data['ticker_setups'].append(ticker_setup)
        
        return jsonify({
            'status': 'success',
            'data': setup_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting setup details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting setup details: {str(e)}'
        }), 500

def register_routes(app):
    """Register routes with the Flask application."""
    app.register_blueprint(setups_bp)
    logger.info("Setup API routes registered")