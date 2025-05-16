"""
Setup Webhook API Module

This module provides API routes for handling trading setup webhook messages.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import app, db
from models import (
    SetupMessage, 
    TickerSetup, 
    Signal, 
    Bias, 
    BiasFlip,
    SignalCategoryEnum,
    AggressivenessEnum,
    ComparisonTypeEnum,
    BiasDirectionEnum
)
from features.setups.parser import SetupParser

# Configure logger
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Create blueprint
webhook_bp = Blueprint('setup_webhook', __name__, url_prefix='/api/v1/webhooks')

# Initialize parser
parser = SetupParser()

def register_routes(app):
    """Register webhook routes with the Flask app."""
    app.register_blueprint(webhook_bp)
    logger.info("Setup webhook routes registered")

@webhook_bp.route('/setup', methods=['POST'])
@limiter.limit("20 per hour")
def receive_setup():
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
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400
        
        # Validate required fields
        if 'text' not in data or not data['text']:
            return jsonify({'status': 'error', 'message': 'Missing required field: text'}), 400
        
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
            return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Parse the message
        setup_message = parser.parse_message(text, date=setup_date, source=source)
        
        # Check if parsing was successful
        if not setup_message or not setup_message.setups:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse any ticker setups from the message',
                'raw_text': text
            }), 400
        
        # Save to database
        try:
            # Create the database model
            db_message = SetupMessage()
            db_message.date = setup_message.date
            db_message.raw_text = setup_message.raw_text
            db_message.source = setup_message.source
            db_message.created_at = datetime.utcnow()
            
            # Add ticker setups
            for setup in setup_message.setups:
                db_ticker = TickerSetup()
                db_ticker.symbol = setup.symbol
                db_ticker.text = setup.text
                
                # Add signals
                for signal in setup.signals:
                    db_signal = Signal()
                    db_signal.category = SignalCategoryEnum(signal.category.value)
                    db_signal.aggressiveness = AggressivenessEnum(signal.aggressiveness.value)
                    db_signal.comparison = ComparisonTypeEnum(signal.comparison.value)
                    
                    # Handle trigger which could be a single value or a range
                    if isinstance(signal.trigger, (int, float)):
                        db_signal.trigger = signal.trigger
                    else:
                        db_signal.trigger = list(signal.trigger)
                    
                    # Handle targets list
                    db_signal.targets = list(signal.targets)
                    
                    db_ticker.signals.append(db_signal)
                
                # Add bias if present
                if setup.bias:
                    db_bias = Bias()
                    db_bias.direction = BiasDirectionEnum(setup.bias.direction.value)
                    db_bias.condition = ComparisonTypeEnum(setup.bias.condition.value)
                    db_bias.price = setup.bias.price
                    
                    # Add bias flip if present
                    if setup.bias.flip:
                        db_bias_flip = BiasFlip()
                        db_bias_flip.direction = BiasDirectionEnum(setup.bias.flip.direction.value)
                        db_bias_flip.price_level = setup.bias.flip.price_level
                        
                        db_bias.bias_flip = db_bias_flip
                    
                    db_ticker.bias = db_bias
                
                db_message.ticker_setups.append(db_ticker)
            
            # Save to database
            db.session.add(db_message)
            db.session.commit()
            
            # Get the message ID
            setup_id = db_message.id
            
            # Return success response
            return jsonify({
                'status': 'success',
                'message': 'Setup message successfully processed',
                'setup_id': setup_id,
                'ticker_count': len(db_message.ticker_setups),
                'ticker_symbols': [ts.symbol for ts in db_message.ticker_setups]
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Database error: {str(e)}',
                'ticker_count': len(setup_message.setups),
                'ticker_symbols': [setup.symbol for setup in setup_message.setups]
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing webhook: {str(e)}'
        }), 500

@webhook_bp.route('/setups/recent', methods=['GET'])
def get_recent_setups():
    """
    Get recent setup messages.
    
    Query parameters:
    - limit: Maximum number of setups to return (default: 10)
    - symbol: Filter by ticker symbol (optional)
    
    Returns:
    - JSON with recent setup messages
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

@webhook_bp.route('/setups/<int:setup_id>', methods=['GET'])
def get_setup_by_id(setup_id):
    """
    Get a setup message by ID.
    
    Args:
        setup_id: ID of the setup message
        
    Returns:
    - JSON with setup message details
    """
    try:
        # Get the message
        message = SetupMessage.query.get(setup_id)
        if not message:
            return jsonify({
                'status': 'error',
                'message': f'Setup with ID {setup_id} not found'
            }), 404
        
        # Convert to response format
        result = {
            'id': message.id,
            'date': message.date.isoformat() if message.date else None,
            'source': message.source,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'raw_text': message.raw_text,
            'ticker_setups': []
        }
        
        # Add ticker setups
        for ts in message.ticker_setups:
            setup_data = {
                'id': ts.id,
                'symbol': ts.symbol,
                'text': ts.text,
                'signals': [],
                'bias': None
            }
            
            # Add signals
            for signal in ts.signals:
                signal_data = {
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': signal.targets
                }
                setup_data['signals'].append(signal_data)
            
            # Add bias if present
            if ts.bias:
                bias_data = {
                    'direction': ts.bias.direction.value,
                    'condition': ts.bias.condition.value,
                    'price': ts.bias.price,
                    'flip': None
                }
                
                # Add bias flip if present
                if ts.bias.bias_flip:
                    bias_data['flip'] = {
                        'direction': ts.bias.bias_flip.direction.value,
                        'price_level': ts.bias.bias_flip.price_level
                    }
                
                setup_data['bias'] = bias_data
            
            result['ticker_setups'].append(setup_data)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting setup: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting setup: {str(e)}'
        }), 500

@webhook_bp.route('/setups/symbol/<symbol>', methods=['GET'])
def get_setups_by_symbol(symbol):
    """
    Get setups for a specific ticker symbol.
    
    Args:
        symbol: Ticker symbol
        
    Query parameters:
    - limit: Maximum number of setups to return (default: 10)
    
    Returns:
    - JSON with setups for the symbol
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=10, type=int)
        
        # Validate limit
        if limit <= 0 or limit > 100:
            return jsonify({
                'status': 'error',
                'message': 'Limit must be between 1 and 100'
            }), 400
        
        # Query ticker setups
        ticker_setups = (TickerSetup.query
            .filter(TickerSetup.symbol == symbol)
            .join(TickerSetup.message)
            .order_by(SetupMessage.date.desc())
            .limit(limit)
            .all())
        
        # Convert to response format
        result = []
        for ts in ticker_setups:
            setup_data = {
                'id': ts.id,
                'symbol': ts.symbol,
                'message_id': ts.message_id,
                'message_date': ts.message.date.isoformat() if ts.message and ts.message.date else None,
                'text': ts.text,
                'signals': [],
                'bias': None
            }
            
            # Add signals
            for signal in ts.signals:
                signal_data = {
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': signal.targets
                }
                setup_data['signals'].append(signal_data)
            
            # Add bias if present
            if ts.bias:
                bias_data = {
                    'direction': ts.bias.direction.value,
                    'condition': ts.bias.condition.value,
                    'price': ts.bias.price,
                    'flip': None
                }
                
                # Add bias flip if present
                if ts.bias.bias_flip:
                    bias_data['flip'] = {
                        'direction': ts.bias.bias_flip.direction.value,
                        'price_level': ts.bias.bias_flip.price_level
                    }
                
                setup_data['bias'] = bias_data
            
            result.append(setup_data)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting setups by symbol: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting setups by symbol: {str(e)}'
        }), 500