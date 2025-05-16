"""
Webhook API Module

This module provides a webhook API endpoint for receiving trading setup messages
and storing them in the database.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from common.db import db
from features.setups.models import (
    SetupMessage, 
    TickerSetup, 
    Signal, 
    Bias,
    SignalTarget,
    SignalCategoryEnum,
    AggressivenessEnum,
    ComparisonTypeEnum,
    BiasDirectionEnum
)
from features.setups.parser import SetupParser

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('setup_webhook', __name__, url_prefix='/api/v1/webhooks')

# Initialize parser
parser = SetupParser()

def register_routes(app):
    """Register webhook routes with the Flask app."""
    app.register_blueprint(webhook_bp)
    logger.info("Setup webhook routes registered")

@webhook_bp.route('/setup', methods=['POST'])
def receive_setup():
    """
    Receive a setup message from a webhook.
    
    Expects JSON payload with:
    - text: The raw setup message text
    - date: (Optional) Date of the setup message (YYYY-MM-DD), defaults to today
    - source: (Optional) Source of the message, defaults to 'webhook'
    
    Returns:
    - JSON with status and parsed ticker setups
    """
    try:
        # Get and validate JSON data
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400
        
        if 'text' not in data or not data['text']:
            return jsonify({'status': 'error', 'message': 'Missing required field: text'}), 400
        
        # Extract data
        text = data.get('text', '').strip()
        source = data.get('source', 'webhook')
        
        # Handle date
        try:
            if 'date' in data and data['date']:
                message_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            else:
                message_date = datetime.now().date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Parse the message
        setup_dto = parser.parse_message(text, message_date=message_date, source=source)
        
        # Check if parsing was successful
        if not setup_dto or not setup_dto.setups:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse any ticker setups from the message',
                'raw_text': text
            }), 400
        
        # Save to database using the consolidated model approach
        try:
            # Create SetupMessage
            db_message = SetupMessage()
            db_message.date = setup_dto.date
            db_message.raw_text = setup_dto.raw_text
            db_message.source = setup_dto.source
            db_message.created_at = datetime.utcnow()
            
            # Add to session
            db.session.add(db_message)
            
            # Flush to get message ID
            db.session.flush()
            
            # Process each ticker setup
            for ticker_setup in setup_dto.setups:
                # Create TickerSetup with direct assignment of setup_id
                db_ticker = TickerSetup()
                db_ticker.symbol = ticker_setup.symbol
                db_ticker.text = ticker_setup.text if ticker_setup.text else ""
                db_ticker.setup_id = db_message.id  # Direct foreign key assignment
                db_ticker.created_at = datetime.utcnow()
                
                # Add to session
                db.session.add(db_ticker)
                db.session.flush()
                
                # Add signals
                for signal_dto in ticker_setup.signals:
                    # Create Signal with direct assignment of ticker_setup_id
                    db_signal = Signal()
                    db_signal.category = signal_dto.category.value  # Store as string instead of enum
                    db_signal.aggressiveness = signal_dto.aggressiveness.value  # Store as string
                    db_signal.comparison = signal_dto.comparison.value  # Store as string
                    db_signal.ticker_setup_id = db_ticker.id  # Direct foreign key assignment
                    db_signal.created_at = datetime.utcnow()
                    db_signal.active = True
                    
                    # Store trigger as JSON
                    if isinstance(signal_dto.trigger, (int, float)):
                        # Single price level
                        db_signal.trigger_value = {"type": "single", "value": float(signal_dto.trigger)}
                    else:
                        # Range
                        db_signal.trigger_value = {
                            "type": "range", 
                            "low": float(signal_dto.trigger[0]), 
                            "high": float(signal_dto.trigger[1])
                        }
                    
                    # Store targets as JSON array
                    db_signal.targets = [float(t) for t in signal_dto.targets]
                    
                    # Add to session
                    db.session.add(db_signal)
                    db.session.flush()
                    
                    # Add targets as separate records in signal_targets table for detailed tracking
                    for i, target_price in enumerate(signal_dto.targets, 1):
                        target = SignalTarget()
                        target.price = float(target_price)
                        target.position = i
                        target.signal_id = db_signal.id  # Direct foreign key assignment
                        target.created_at = datetime.utcnow()
                        
                        # Add to session
                        db.session.add(target)
                
                # Add bias if present
                if ticker_setup.bias:
                    db_bias = Bias()
                    db_bias.direction = ticker_setup.bias.direction.value  # Store as string
                    db_bias.condition = ticker_setup.bias.condition.value  # Store as string
                    db_bias.price = float(ticker_setup.bias.price)
                    db_bias.ticker_setup_id = db_ticker.id  # Direct foreign key assignment
                    db_bias.created_at = datetime.utcnow()
                    
                    # Add flip details if present
                    if ticker_setup.bias.flip:
                        db_bias.flip_direction = ticker_setup.bias.flip.direction.value  # Store as string
                        db_bias.flip_price_level = float(ticker_setup.bias.flip.price_level)
                    
                    # Add to session
                    db.session.add(db_bias)
            
            # Commit all changes
            db.session.commit()
            
            # Return success response
            return jsonify({
                'status': 'success',
                'message': 'Setup message successfully processed',
                'setup_id': db_message.id,
                'ticker_count': len(db_message.ticker_setups),
                'tickers': [ts.symbol for ts in db_message.ticker_setups]
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Database error: {str(e)}',
                'parsed': {
                    'ticker_count': len(setup_dto.setups),
                    'tickers': [s.symbol for s in setup_dto.setups]
                }
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
                # Determine trigger value
                if signal.trigger_price is not None:
                    trigger = signal.trigger_price
                elif signal.trigger_low is not None and signal.trigger_high is not None:
                    trigger = [signal.trigger_low, signal.trigger_high]
                else:
                    trigger = None
                
                signal_data = {
                    'id': signal.id,
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': trigger,
                    'targets': [target.price for target in signal.targets]
                }
                setup_data['signals'].append(signal_data)
            
            # Add bias if present
            if ts.bias:
                bias_data = {
                    'id': ts.bias.id,
                    'direction': ts.bias.direction.value,
                    'condition': ts.bias.condition.value,
                    'price': ts.bias.price,
                    'flip': None
                }
                
                # Add flip details if present
                if ts.bias.flip_direction and ts.bias.flip_price:
                    bias_data['flip'] = {
                        'direction': ts.bias.flip_direction.value,
                        'price_level': ts.bias.flip_price
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
                # Determine trigger value
                if signal.trigger_price is not None:
                    trigger = signal.trigger_price
                elif signal.trigger_low is not None and signal.trigger_high is not None:
                    trigger = [signal.trigger_low, signal.trigger_high]
                else:
                    trigger = None
                
                signal_data = {
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': trigger,
                    'targets': [target.price for target in signal.targets]
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
                
                # Add flip details if present
                if ts.bias.flip_direction and ts.bias.flip_price:
                    bias_data['flip'] = {
                        'direction': ts.bias.flip_direction.value,
                        'price_level': ts.bias.flip_price
                    }
                
                setup_data['bias'] = bias_data
            
            result.append(setup_data)
        
        return jsonify({
            'status': 'success',
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting setups by symbol: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting setups by symbol: {str(e)}'
        }), 500