"""
Trading Setups API Module

Consolidated API endpoints for retrieving and managing trading setups.
"""
import datetime
import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from common.db import db
from common.db_models import SetupModel, TickerSetupModel, SignalModel
from features.setups.service import SetupService

# Create blueprint
bp = Blueprint('setups_api', __name__, url_prefix='/api/setups')
logger = logging.getLogger(__name__)

def get_setup_service():
    """Dependency injection for SetupService."""
    return SetupService()

@bp.route('/webhook', methods=['POST']) 
def receive_setup_webhook():
    """Receive and process a setup message from webhook."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        service = get_setup_service()
        success, response = service.process_webhook(
            payload=data,
            signature=request.headers.get('X-Webhook-Signature')
        )

        if success:
            return jsonify(response), 201
        return jsonify(response), 400

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing webhook: {str(e)}'
        }), 500

@bp.route('/active', methods=['GET'])
def get_active_setups():
    """Get active trading setups for the current day."""
    try:
        setups = SetupService.get_active_setups()
        return jsonify({
            'status': 'success',
            'setups': setups
        })
    except Exception as e:
        logger.error(f"Error getting active setups: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': 'Error retrieving active setups'
        }), 500

@bp.route('/historical', methods=['GET'])
def get_historical_setups():
    """Get historical trading setups for a specified date."""
    try:
        date_str = request.args.get('date')
        if date_str:
            try:
                requested_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        else:
            requested_date = datetime.date.today()

        setups = SetupService.get_historical_setups(requested_date)
        return jsonify({
            'status': 'success',
            'date': requested_date.isoformat(),
            'setups': setups
        })
    except Exception as e:
        logger.error(f"Error getting historical setups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving historical setups'
        }), 500

@bp.route('/ticker/<symbol>', methods=['GET'])
def get_ticker_setups(symbol):
    """Get all trading setups for a specific ticker symbol."""
    try:
        limit = request.args.get('limit', default=10, type=int)
        if limit <= 0 or limit > 100:
            return jsonify({
                'status': 'error',
                'message': 'Limit must be between 1 and 100'
            }), 400

        service = get_setup_service()
        setups = service.get_setups_by_symbol(symbol=symbol.upper(), limit=limit)
        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'count': len(setups),
            'setups': setups
        })
    except Exception as e:
        logger.error(f"Error getting setups for ticker {symbol}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving setups for {symbol}'
        }), 500

@bp.route('/detail/<int:setup_id>', methods=['GET'])
def get_setup_detail(setup_id):
    """Get detailed information for a specific setup."""
    try:
        service = get_setup_service()
        setup = service.get_setup_by_id(setup_id)
        if not setup:
            return jsonify({
                'status': 'error',
                'message': f'Setup with ID {setup_id} not found'
            }), 404

        return jsonify({
            'status': 'success',
            'setup': setup
        })
    except Exception as e:
        logger.error(f"Error getting setup detail: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving setup details'
        }), 500

def register_routes(app):
    """Register the setups API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Setups API routes registered")