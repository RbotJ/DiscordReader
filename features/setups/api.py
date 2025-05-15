"""
API endpoints for trading setups.

This module provides routes for submitting, retrieving, and managing trade setups.
"""
import logging
from flask import Blueprint, request, jsonify
from common.db_models import (
    SetupModel, 
    TickerSetupModel, 
    SignalModel, 
    BiasModel
)
from app import db
from features.setups.parser import process_setup_message, parse_setup_message

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
setup_routes = Blueprint('setups', __name__)

@setup_routes.route('/api/setups', methods=['POST'])
def create_setup():
    """Submit a new trading setup message."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Validate input
    if 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
    
    # Process the setup message
    source = data.get('source', 'manual')
    result = process_setup_message(data['message'], source)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@setup_routes.route('/api/setups', methods=['GET'])
def get_setups():
    """Get all trading setups."""
    try:
        # Query all setups
        setups = db.session.query(SetupModel).order_by(SetupModel.date.desc()).all()
        
        # Format the response
        response = []
        for setup in setups:
            setup_data = {
                "id": setup.id,
                "date": setup.date.isoformat(),
                "source": setup.source,
                "created_at": setup.created_at.isoformat(),
                "ticker_count": len(setup.ticker_setups)
            }
            response.append(setup_data)
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error retrieving setups: {e}")
        return jsonify({"error": str(e)}), 500

@setup_routes.route('/api/setups/<int:setup_id>', methods=['GET'])
def get_setup(setup_id):
    """Get a specific trading setup."""
    try:
        # Query the setup
        setup = db.session.query(SetupModel).filter_by(id=setup_id).first()
        
        if not setup:
            return jsonify({"error": "Setup not found"}), 404
        
        # Format the response
        response = {
            "id": setup.id,
            "date": setup.date.isoformat(),
            "source": setup.source,
            "created_at": setup.created_at.isoformat(),
            "raw_text": setup.raw_text,
            "tickers": []
        }
        
        # Add tickers
        for ticker in setup.ticker_setups:
            ticker_data = {
                "id": ticker.id,
                "symbol": ticker.symbol,
                "signals": [],
                "bias": None
            }
            
            # Add signals
            for signal in ticker.signals:
                signal_data = {
                    "id": signal.id,
                    "category": signal.category,
                    "aggressiveness": signal.aggressiveness,
                    "comparison": signal.comparison,
                    "trigger_value": signal.trigger_value,
                    "targets": signal.targets,
                    "active": signal.active,
                    "triggered_at": signal.triggered_at.isoformat() if signal.triggered_at else None
                }
                ticker_data["signals"].append(signal_data)
            
            # Add bias
            if ticker.bias:
                bias = ticker.bias
                bias_data = {
                    "id": bias.id,
                    "direction": bias.direction,
                    "condition": bias.condition,
                    "price": bias.price,
                    "flip_direction": bias.flip_direction,
                    "flip_price_level": bias.flip_price_level
                }
                ticker_data["bias"] = bias_data
            
            response["tickers"].append(ticker_data)
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error retrieving setup {setup_id}: {e}")
        return jsonify({"error": str(e)}), 500

@setup_routes.route('/api/tickers/<symbol>/latest_setup', methods=['GET'])
def get_latest_ticker_setup(symbol):
    """Get the latest setup for a specific ticker."""
    try:
        # Find the most recent ticker setup
        ticker_setup = db.session.query(TickerSetupModel).join(
            SetupModel, SetupModel.id == TickerSetupModel.setup_id
        ).filter(
            TickerSetupModel.symbol == symbol.upper()
        ).order_by(
            SetupModel.date.desc()
        ).first()
        
        if not ticker_setup:
            return jsonify({"error": f"No setups found for {symbol}"}), 404
        
        # Format the response
        response = {
            "id": ticker_setup.id,
            "symbol": ticker_setup.symbol,
            "setup_id": ticker_setup.setup_id,
            "setup_date": ticker_setup.setup.date.isoformat(),
            "signals": [],
            "bias": None
        }
        
        # Add signals
        for signal in ticker_setup.signals:
            signal_data = {
                "id": signal.id,
                "category": signal.category,
                "aggressiveness": signal.aggressiveness,
                "comparison": signal.comparison,
                "trigger_value": signal.trigger_value,
                "targets": signal.targets,
                "active": signal.active,
                "triggered_at": signal.triggered_at.isoformat() if signal.triggered_at else None
            }
            response["signals"].append(signal_data)
        
        # Add bias
        if ticker_setup.bias:
            bias = ticker_setup.bias
            bias_data = {
                "id": bias.id,
                "direction": bias.direction,
                "condition": bias.condition,
                "price": bias.price,
                "flip_direction": bias.flip_direction,
                "flip_price_level": bias.flip_price_level
            }
            response["bias"] = bias_data
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error retrieving latest setup for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@setup_routes.route('/api/signals/active', methods=['GET'])
def get_active_signals():
    """Get all active signals."""
    try:
        # Query active signals
        active_signals = db.session.query(SignalModel).filter_by(active=True).all()
        
        # Format the response
        response = []
        for signal in active_signals:
            signal_data = {
                "id": signal.id,
                "symbol": signal.ticker_setup.symbol,
                "category": signal.category,
                "aggressiveness": signal.aggressiveness,
                "comparison": signal.comparison,
                "trigger_value": signal.trigger_value,
                "targets": signal.targets,
                "setup_date": signal.ticker_setup.setup.date.isoformat()
            }
            response.append(signal_data)
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error retrieving active signals: {e}")
        return jsonify({"error": str(e)}), 500

@setup_routes.route('/api/signals/<int:signal_id>/deactivate', methods=['POST'])
def deactivate_signal(signal_id):
    """Deactivate a signal."""
    try:
        # Find the signal
        signal = db.session.query(SignalModel).filter_by(id=signal_id).first()
        
        if not signal:
            return jsonify({"error": "Signal not found"}), 404
        
        # Use SQL update to avoid Column assignment issues
        db.session.execute(
            db.update(SignalModel)
            .where(SignalModel.id == signal_id)
            .values(active=False)
        )
        db.session.commit()
        
        return jsonify({"success": True, "message": f"Signal {signal_id} deactivated"}), 200
    
    except Exception as e:
        logger.error(f"Error deactivating signal {signal_id}: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@setup_routes.route('/api/parser/test', methods=['POST'])
def test_parser():
    """Test the setup parser without saving to database."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Validate input
    if 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
    
    try:
        # Parse the message
        source = data.get('source', 'test')
        setup = parse_setup_message(data['message'], source)
        
        # Convert to dictionary for JSON response
        result = {
            "date": setup.date.isoformat(),
            "source": setup.source,
            "tickers": [],
            "ticker_count": len(setup.setups),
            "signal_count": sum(len(s.signals) for s in setup.setups)
        }
        
        # Add tickers
        for ticker_setup in setup.setups:
            ticker_data = {
                "symbol": ticker_setup.symbol,
                "signals": [],
                "has_bias": ticker_setup.bias is not None
            }
            
            # Add signals
            for signal in ticker_setup.signals:
                signal_data = {
                    "category": signal.category.value,
                    "aggressiveness": signal.aggressiveness.value,
                    "comparison": signal.comparison.value,
                    "trigger": signal.trigger,
                    "targets": signal.targets
                }
                ticker_data["signals"].append(signal_data)
            
            result["tickers"].append(ticker_data)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error testing parser: {e}")
        return jsonify({"error": str(e)}), 500