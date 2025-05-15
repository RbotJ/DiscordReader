"""
Setups API Module

This module provides endpoints for receiving trading setup messages
and storing them in the database.
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from common.db_models import SetupModel, TickerSetupModel, SignalModel, BiasModel
from common.models import TradeSetupMessage, Signal, Bias, BiasFlip
from features.setups.parser import parse_setup_message
from features.setups.event_publisher import publish_setup_message_created
from features.setups.auth import require_auth

logger = logging.getLogger(__name__)
setups_blueprint = Blueprint('setups', __name__)


def create_setup_from_message(setup_message: TradeSetupMessage) -> SetupModel:
    """
    Create database models from a parsed setup message.
    
    Args:
        setup_message: The parsed trade setup message
        
    Returns:
        SetupModel: The created database model
    """
    # Create the main setup
    setup = SetupModel()
    setup.date = setup_message.date
    setup.raw_text = setup_message.raw_text
    setup.source = setup_message.source
    setup.created_at = setup_message.created_at
    
    db.session.add(setup)
    db.session.flush()  # Flush to get the ID
    
    # Create ticker setups
    for ticker_setup in setup_message.setups:
        ticker = TickerSetupModel()
        ticker.setup_id = setup.id
        ticker.symbol = ticker_setup.symbol
        ticker.created_at = datetime.utcnow()
        
        db.session.add(ticker)
        db.session.flush()  # Flush to get the ID
        
        # Create signals
        for signal in ticker_setup.signals:
            # Convert trigger to JSON-compatible format
            trigger_value = signal.trigger
            if isinstance(trigger_value, list):
                trigger_json = trigger_value
            else:
                trigger_json = float(trigger_value)
            
            signal_model = SignalModel()
            signal_model.ticker_setup_id = ticker.id
            signal_model.category = signal.category.value
            signal_model.aggressiveness = signal.aggressiveness.value
            signal_model.comparison = signal.comparison.value
            signal_model.trigger_value = trigger_json
            signal_model.targets = signal.targets
            signal_model.active = True
            signal_model.created_at = datetime.utcnow()
            
            db.session.add(signal_model)
        
        # Create bias if exists
        if ticker_setup.bias:
            flip_direction = None
            flip_price_level = None
            
            if ticker_setup.bias.flip:
                flip_direction = ticker_setup.bias.flip.direction.value
                flip_price_level = ticker_setup.bias.flip.price_level
            
            bias_model = BiasModel()
            bias_model.ticker_setup_id = ticker.id
            bias_model.direction = ticker_setup.bias.direction.value
            bias_model.condition = ticker_setup.bias.condition.value
            bias_model.price = ticker_setup.bias.price
            bias_model.flip_direction = flip_direction
            bias_model.flip_price_level = flip_price_level
            bias_model.created_at = datetime.utcnow()
            
            db.session.add(bias_model)
    
    return setup


@setups_blueprint.route('/api/setups/webhook', methods=['POST'])
@require_auth
def setup_webhook():
    """
    Endpoint for receiving trading setup webhook messages.
    
    Accepts webhook POST requests with raw text messages.
    Parses the message and stores in the database.
    Requires valid authentication signature in headers.
    
    Returns:
        JSON response with status
    """
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        return jsonify({'error': 'Missing required field: text'}), 400
    
    try:
        # Parse the message
        source = data.get('source', 'webhook')
        setup_message = parse_setup_message(data['text'], source)
        
        # Check if we got any valid setups
        if not setup_message.setups:
            return jsonify({
                'status': 'warning',
                'message': 'No valid trading setups found in the message'
            }), 200
        
        # Store in database
        with current_app.app_context():
            try:
                setup = create_setup_from_message(setup_message)
                db.session.commit()
                
                # Publish setup message to Redis
                publish_result = publish_setup_message_created(setup)
                if publish_result:
                    logger.info(f"Successfully published setup events for setup ID {setup.id}")
                else:
                    logger.warning(f"Failed to publish setup events for setup ID {setup.id}")
                
                logger.info(f"Processed setup message with {len(setup_message.setups)} tickers")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Successfully processed setup with {len(setup_message.setups)} tickers',
                    'setup_id': setup.id,
                    'tickers': [ticker_setup.symbol for ticker_setup in setup_message.setups],
                    'events_published': publish_result
                }), 201
                
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Database error occurred'
                }), 500
    
    except Exception as e:
        logger.exception(f"Error processing setup message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing the message: {str(e)}'
        }), 500


@setups_blueprint.route('/api/setups/parse', methods=['POST'])
def parse_setup():
    """
    Endpoint for parsing a setup message without storing it.
    
    Useful for testing/validating setup messages.
    
    Returns:
        JSON response with parsed data
    """
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        return jsonify({'error': 'Missing required field: text'}), 400
    
    try:
        # Parse the message
        source = data.get('source', 'test')
        setup_message = parse_setup_message(data['text'], source)
        
        # Convert to dictionary for JSON response
        result = setup_message.dict()
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.exception(f"Error parsing setup message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error parsing the message: {str(e)}'
        }), 500


@setups_blueprint.route('/api/setups', methods=['GET'])
def get_setups():
    """
    Get all setup messages.
    
    Returns:
        JSON response with setups data
    """
    try:
        setups = SetupModel.query.order_by(SetupModel.date.desc()).all()
        
        result = []
        for setup in setups:
            ticker_setups = []
            for ticker in setup.ticker_setups:
                ticker_data = {
                    'id': ticker.id,
                    'symbol': ticker.symbol,
                    'signal_count': len(ticker.signals),
                    'has_bias': ticker.bias is not None
                }
                ticker_setups.append(ticker_data)
            
            setup_data = {
                'id': setup.id,
                'date': setup.date.isoformat(),
                'source': setup.source,
                'created_at': setup.created_at.isoformat(),
                'ticker_count': len(ticker_setups),
                'tickers': ticker_setups
            }
            result.append(setup_data)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving setups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving setups: {str(e)}'
        }), 500


@setups_blueprint.route('/api/setups/<int:setup_id>', methods=['GET'])
def get_setup(setup_id):
    """
    Get a specific setup message by ID.
    
    Args:
        setup_id: The ID of the setup to retrieve
        
    Returns:
        JSON response with setup data
    """
    try:
        setup = SetupModel.query.get(setup_id)
        
        if not setup:
            return jsonify({
                'status': 'error',
                'message': 'Setup not found'
            }), 404
        
        # Convert to structured format
        result = {
            'id': setup.id,
            'date': setup.date.isoformat(),
            'raw_text': setup.raw_text,
            'source': setup.source,
            'created_at': setup.created_at.isoformat(),
            'tickers': []
        }
        
        for ticker in setup.ticker_setups:
            ticker_data = {
                'id': ticker.id,
                'symbol': ticker.symbol,
                'signals': [],
                'bias': None
            }
            
            # Add signals
            for signal in ticker.signals:
                trigger_value = signal.trigger_value
                if isinstance(trigger_value, str):
                    try:
                        trigger_value = json.loads(trigger_value)
                    except Exception:
                        pass
                
                signal_data = {
                    'id': signal.id,
                    'category': signal.category,
                    'aggressiveness': signal.aggressiveness,
                    'comparison': signal.comparison,
                    'trigger': trigger_value,
                    'targets': signal.targets,
                    'active': signal.active,
                    'triggered_at': signal.triggered_at.isoformat() if signal.triggered_at else None
                }
                ticker_data['signals'].append(signal_data)
            
            # Add bias if exists
            if ticker.bias:
                bias = ticker.bias
                bias_data = {
                    'id': bias.id,
                    'direction': bias.direction,
                    'condition': bias.condition,
                    'price': bias.price,
                    'flip': None
                }
                
                if bias.flip_direction and bias.flip_price_level:
                    bias_data['flip'] = {
                        'direction': bias.flip_direction,
                        'price_level': bias.flip_price_level
                    }
                
                ticker_data['bias'] = bias_data
            
            result['tickers'].append(ticker_data)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving setup {setup_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving setup: {str(e)}'
        }), 500


def register_routes(app):
    """Register setup routes with the Flask app."""
    app.register_blueprint(setups_blueprint)
    logger.info("Setup routes registered")