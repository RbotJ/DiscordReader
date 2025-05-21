"""
Market Data API Module

This module provides API endpoints for retrieving market data,
including prices, candlestick data, and market status.
"""

import datetime
import logging
from flask import Blueprint, jsonify, request
from features.alpaca.client import get_trading_client

# Create blueprint
bp = Blueprint('market_api', __name__, url_prefix='/api/market')
logger = logging.getLogger(__name__)

@bp.route('/status', methods=['GET'])
def get_market_status():
    """
    Get the current market status.

    Returns:
        JSON response with market status information
    """
    try:
        client = get_trading_client()
        if not client:
            return jsonify({
                'status': 'error',
                'message': 'Trading client not initialized'
            }), 500

        # Get market clock
        clock = client.get_clock()

        # Get account status
        account = client.get_account()

        return jsonify({
            'status': 'success',
            'is_open': clock.is_open,
            'next_open': clock.next_open.isoformat() if clock.next_open else None,
            'next_close': clock.next_close.isoformat() if clock.next_close else None,
            'current_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'trading_blocked': account.trading_blocked,
            'account_blocked': account.account_blocked
        })

    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving market status'
        }), 500

def register_routes(app):
    """Register the market API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Market API routes registered")

# Expose market routes for importing in other modules
market_routes = bp