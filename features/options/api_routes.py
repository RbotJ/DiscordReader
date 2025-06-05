"""
Options Data API Routes

This module provides API endpoints for options data, including
options chains, contract pricing, and selection.
"""
import logging
from flask import Blueprint, jsonify, request
from datetime import datetime

from features.options.pricing import get_options_pricing
from common.events import publish_event, EventChannels
from common.db import db

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('options', __name__, url_prefix='/api/options')

def register_routes(app):
    """Register options routes with the Flask app"""
    app.register_blueprint(bp)
    logger.info("Options API routes registered")

@bp.route('/chain/<symbol>', methods=['GET'])
def get_option_chain(symbol):
    """
    Get option chain for a symbol.

    Query params:
        expiration: Expiration date (YYYY-MM-DD, optional)

    Returns:
        JSON with option chain data
    """
    try:
        # Parse query parameters
        expiration = request.args.get('expiration')

        # Get options pricing service
        options_pricing = get_options_pricing()

        # Get option chain
        chain = options_pricing.get_option_chain(symbol, expiration)

        if not chain:
            return jsonify({
                'status': 'error',
                'message': f'No option chain data available for {symbol}'
            }), 404

        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'expiration_date': chain.get('expiration_date'),
            'chain': chain
        })
    except Exception as e:
        logger.error(f"Error getting option chain for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving option chain for {symbol}'
        }), 500

@bp.route('/expirations/<symbol>', methods=['GET'])
def get_expiration_dates(symbol):
    """
    Get available expiration dates for a symbol.

    Returns:
        JSON with expiration dates
    """
    try:
        # Get options pricing service
        options_pricing = get_options_pricing()

        # Get expiration dates
        dates = options_pricing.get_expiration_dates(symbol)

        if not dates:
            return jsonify({
                'status': 'error',
                'message': f'No expiration dates available for {symbol}'
            }), 404

        # Convert dates to strings
        date_strings = [date.isoformat() for date in dates]

        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'expiration_dates': date_strings
        })
    except Exception as e:
        logger.error(f"Error getting expiration dates for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving expiration dates for {symbol}'
        }), 500

@bp.route('/near-the-money/<symbol>', methods=['GET'])
def get_near_the_money(symbol):
    """
    Get near-the-money options for a symbol.

    Query params:
        expiration: Expiration date (YYYY-MM-DD, optional)
        strikes: Number of strikes above and below (default: 5)
        price: Underlying price to use (optional)

    Returns:
        JSON with near-the-money options
    """
    try:
        # Parse query parameters
        expiration = request.args.get('expiration')
        strikes = int(request.args.get('strikes', 5))
        price = request.args.get('price')

        # Convert price to float if provided
        underlying_price = float(price) if price else None

        # Get options pricing service
        options_pricing = get_options_pricing()

        # Get near-the-money options
        options = options_pricing.get_near_the_money_options(
            symbol, expiration, strikes, underlying_price
        )

        if not options:
            return jsonify({
                'status': 'error',
                'message': f'No near-the-money options available for {symbol}'
            }), 404

        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'underlying_price': options.get('underlying_price'),
            'options': options
        })
    except Exception as e:
        logger.error(f"Error getting near-the-money options for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving near-the-money options for {symbol}'
        }), 500

@bp.route('/odte/<symbol>', methods=['GET'])
def get_odte_options(symbol):
    """
    Get 0 DTE (Days To Expiration) options for a symbol.

    Query params:
        strikes: Number of strikes above and below (default: 5)

    Returns:
        JSON with 0 DTE options
    """
    try:
        # Parse query parameters
        strikes = int(request.args.get('strikes', 5))

        # Get options pricing service
        options_pricing = get_options_pricing()

        # Get 0 DTE options
        options = options_pricing.get_odte_options(symbol, strikes)

        if not options:
            return jsonify({
                'status': 'error',
                'message': f'No 0 DTE options available for {symbol}'
            }), 404

        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'underlying_price': options.get('underlying_price'),
            'options': options
        })
    except Exception as e:
        logger.error(f"Error getting 0 DTE options for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving 0 DTE options for {symbol}'
        }), 500

@bp.route('/contract-for-signal/<symbol>', methods=['POST'])
def select_contract_for_signal(symbol):
    """
    Select optimal options contract based on a trading signal.

    Expected JSON payload:
        {
            "signal_type": "breakout|breakdown|rejection|bounce",
            "price_level": 123.45,
            "risk_amount": 500.0,
            "expiration": "2023-05-15", (optional)
            "aggressiveness": "conservative|medium|aggressive" (default: medium)
        }

    Returns:
        JSON with selected contract
    """
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Missing request data'
            }), 400

        # Extract parameters
        signal_type = data.get('signal_type')
        price_level = data.get('price_level')
        risk_amount = data.get('risk_amount', 500.0)
        expiration = data.get('expiration')
        aggressiveness = data.get('aggressiveness', 'medium')

        # Validate required parameters
        if not signal_type or price_level is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters: signal_type and price_level'
            }), 400

        # Get options selector service
        options_selector = get_options_selector()

        # Select contract
        contract = options_selector.select_contract_for_signal(
            symbol, signal_type, price_level, risk_amount, expiration, aggressiveness
        )

        if not contract:
            return jsonify({
                'status': 'error',
                'message': f'No suitable contract found for {symbol} with signal {signal_type}'
            }), 404

        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'signal_type': signal_type,
            'contract': contract
        })
    except Exception as e:
        logger.error(f"Error selecting contract for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error selecting contract for {symbol}'
        }), 500

def register_routes(app):
    """Register options API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Options API routes registered")