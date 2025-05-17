"""
Webhook API Module

This module provides a webhook API endpoint for receiving trading setup messages
and storing them in the database.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

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
from features.setups.parser import parse_setup_message

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('setup_webhook', __name__, url_prefix='/api/webhooks')

def register_routes(app):
    """Register webhook routes with the Flask app."""
    app.register_blueprint(webhook_bp)
    logger.info("Setup webhook routes registered")

@webhook_bp.route('/setup', methods=['POST'])
def receive_setup():
    """
    Receive a setup message from a webhook.
    
    Expected JSON payload:
    {
        "text": "A+ Setups for the day...",
        "source": "discord",
        "timestamp": "2023-03-14T12:00:00Z" (optional)
    }
    
    Returns:
        JSON response with parsing results
    """
    # Validate request
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
    
    # Get message metadata
    message_text = data['text']
    source = data.get('source', 'webhook')
    timestamp = data.get('timestamp')
    
    try:
        # Parse the setup message
        setup_dto = parse_setup_message(message_text, source=source)
        
        if not setup_dto.ticker_setups:
            return jsonify({
                'success': False,
                'error': 'No valid trading setups found in message',
                'code': 'NO_SETUPS_FOUND'
            }), 400
        
        # Store in database
        from app import db
        
        # Create main setup message
        setup_message = SetupMessage(
            date=setup_dto.date,
            raw_text=setup_dto.raw_text,
            source=setup_dto.source,
            created_at=datetime.utcnow()
        )
        
        db.session.add(setup_message)
        db.session.flush()  # Get ID without committing
        
        # Create ticker setups and signals
        for ticker_setup_dto in setup_dto.ticker_setups:
            # Create ticker setup
            ticker_setup = TickerSetup(
                symbol=ticker_setup_dto.symbol,
                text=ticker_setup_dto.text,
                message_id=setup_message.id
            )
            
            db.session.add(ticker_setup)
            db.session.flush()  # Get ID without committing
            
            # Create signals
            for signal_dto in ticker_setup_dto.signals:
                signal = Signal(
                    ticker_setup_id=ticker_setup.id,
                    category=signal_dto.category,
                    aggressiveness=signal_dto.aggressiveness,
                    comparison=signal_dto.comparison,
                    trigger={"price": signal_dto.trigger, "timeframe": "1D"},
                    targets=[{"price": t, "percentage": 1.0/len(signal_dto.targets)} for t in signal_dto.targets]
                )
                db.session.add(signal)
            
            # Create bias if present
            if ticker_setup_dto.bias:
                bias = Bias(
                    ticker_setup_id=ticker_setup.id,
                    direction=ticker_setup_dto.bias.direction,
                    condition=ticker_setup_dto.bias.condition,
                    price=ticker_setup_dto.bias.price
                )
                db.session.add(bias)
                db.session.flush()
                
                # Add bias flip if present
                if ticker_setup_dto.bias.flip:
                    bias_flip = BiasFlip(
                        bias_id=bias.id,
                        direction=ticker_setup_dto.bias.flip.direction,
                        price_level=ticker_setup_dto.bias.flip.price_level
                    )
                    db.session.add(bias_flip)
        
        # Commit all changes
        db.session.commit()
        
        # Return success response with parsed data
        return jsonify({
            'success': True,
            'message_id': setup_message.id,
            'date': setup_dto.date.isoformat(),
            'tickers': [setup.symbol for setup in setup_dto.setups],
            'signal_count': sum(len(setup.signals) for setup in setup_dto.setups)
        })
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': f"Error processing webhook: {str(e)}",
            'code': 'PROCESSING_ERROR'
        }), 500

@webhook_bp.route('/setup/parse', methods=['POST'])
def parse_setup():
    """
    Parse a setup message without saving to the database.
    
    Expected JSON payload:
    {
        "text": "A+ Setups for the day...",
        "source": "test" (optional)
    }
    
    Returns:
        JSON response with parsing results
    """
    # Validate request
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
    
    # Get message metadata
    message_text = data['text']
    source = data.get('source', 'test')
    
    try:
        # Parse the setup message without saving
        setup_dto = parse_setup_message(message_text, source=source)
        
        # Prepare response
        ticker_details = []
        for ticker_setup in setup_dto.ticker_setups:
            # Convert signals to dictionaries
            signals = []
            for signal in ticker_setup.signals:
                signal_dict = {
                    'category': signal.category.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': list(signal.targets),
                    'aggressiveness': signal.aggressiveness.value
                }
                signals.append(signal_dict)
            
            # Convert bias to dictionary if present
            bias = None
            if ticker_setup.bias:
                bias = {
                    'direction': ticker_setup.bias.direction.value,
                    'condition': ticker_setup.bias.condition.value,
                    'price': ticker_setup.bias.price
                }
                
                # Add flip if present
                if ticker_setup.bias.flip:
                    bias['flip'] = {
                        'direction': ticker_setup.bias.flip.direction.value,
                        'price_level': ticker_setup.bias.flip.price_level
                    }
            
            # Create ticker detail
            ticker_detail = {
                'symbol': ticker_setup.symbol,
                'signals': signals,
                'bias': bias
            }
            ticker_details.append(ticker_detail)
        
        # Return success response with parsed data
        return jsonify({
            'success': True,
            'date': setup_dto.date.isoformat(),
            'tickers': ticker_details
        })
    
    except Exception as e:
        logger.error(f"Error parsing setup message: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': f"Error parsing setup message: {str(e)}",
            'code': 'PARSING_ERROR'
        }), 500