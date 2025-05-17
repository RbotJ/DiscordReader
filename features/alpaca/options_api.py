"""
Options API Module

This module provides API routes for options data and trading functionality.
"""
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app

from features.alpaca.options import get_options_fetcher
from features.execution.options_trader import get_options_trader

logger = logging.getLogger(__name__)

options_api = Blueprint('options_api', __name__)


@options_api.route('/api/options/chain/<ticker>', methods=['GET'])
def get_options_chain(ticker):
    """
    Get options chain for a ticker.
    
    Args:
        ticker: Ticker symbol
        
    Query params:
        expiration: Optional expiration date (YYYY-MM-DD)
        strike: Optional strike price
        type: Optional option type ('call' or 'put')
        force_refresh: Whether to force refresh from API (default: false)
    """
    try:
        options_fetcher = get_options_fetcher()
        if not options_fetcher:
            return jsonify({
                'status': 'error',
                'message': 'Options fetcher not available'
            }), 500
            
        # Parse query parameters
        expiration = request.args.get('expiration')
        strike_price = request.args.get('strike')
        option_type = request.args.get('type')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Convert strike price to float if present
        if strike_price:
            try:
                strike_price = float(strike_price)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid strike price'
                }), 400
                
        # Get options chain
        options_chain = options_fetcher.get_chain(
            symbol=ticker,
            expiration=expiration,
            strike_price=strike_price,
            option_type=option_type,
            force_refresh=force_refresh
        )
        
        return jsonify({
            'status': 'success',
            'data': options_chain,
            'count': len(options_chain)
        })
        
    except Exception as e:
        logger.error(f"Error fetching options chain for {ticker}: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Error fetching options chain: {str(e)}"
        }), 500


@options_api.route('/api/options/expirations/<ticker>', methods=['GET'])
def get_options_expirations(ticker):
    """
    Get available expiration dates for a ticker.
    
    Args:
        ticker: Ticker symbol
    """
    try:
        options_fetcher = get_options_fetcher()
        if not options_fetcher:
            return jsonify({
                'status': 'error',
                'message': 'Options fetcher not available'
            }), 500
            
        # Get all options to extract expirations
        options_chain = options_fetcher.get_chain(symbol=ticker)
        
        # Extract unique expiration dates
        expirations = set()
        for contract in options_chain:
            if 'expiration' in contract:
                expirations.add(contract['expiration'])
                
        # Sort expirations
        sorted_expirations = sorted(list(expirations))
        
        return jsonify({
            'status': 'success',
            'data': sorted_expirations,
            'count': len(sorted_expirations)
        })
        
    except Exception as e:
        logger.error(f"Error fetching options expirations for {ticker}: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Error fetching options expirations: {str(e)}"
        }), 500


@options_api.route('/api/options/atm/<ticker>', methods=['GET'])
def get_atm_options(ticker):
    """
    Get at-the-money options for a ticker.
    
    Args:
        ticker: Ticker symbol
        
    Query params:
        type: Option type ('call' or 'put', default is call)
        delta: Target delta value (default: 0.50)
        expiration: Optional specific expiration date
    """
    try:
        options_fetcher = get_options_fetcher()
        if not options_fetcher:
            return jsonify({
                'status': 'error',
                'message': 'Options fetcher not available'
            }), 500
            
        # Parse query parameters
        option_type = request.args.get('type', 'call').lower()
        delta = request.args.get('delta', '0.50')
        expiration = request.args.get('expiration')
        
        # Convert delta to float
        try:
            target_delta = float(delta)
        except ValueError:
            target_delta = 0.50
            
        # Get ATM option
        contract = options_fetcher.find_atm_options(
            symbol=ticker,
            option_type=option_type,
            target_delta=target_delta,
            expiration=expiration
        )
        
        if not contract:
            return jsonify({
                'status': 'error',
                'message': f"No suitable {option_type} option found for {ticker}"
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': contract
        })
        
    except Exception as e:
        logger.error(f"Error fetching ATM option for {ticker}: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Error fetching ATM option: {str(e)}"
        }), 500


@options_api.route('/api/options/trade', methods=['POST'])
def execute_options_trade():
    """
    Execute an options trade based on a signal.
    
    Expected JSON payload:
    {
        "ticker": "SPY",
        "direction": "long",  # or "short"
        "targets": [
            {"price": 455.0, "percentage": 0.50},
            {"price": 460.0, "percentage": 0.50}
        ]
    }
    """
    try:
        options_trader = get_options_trader()
        if not options_trader:
            return jsonify({
                'status': 'error',
                'message': 'Options trader not available'
            }), 500
            
        # Get signal data from request
        signal = request.json
        if not signal:
            return jsonify({
                'status': 'error',
                'message': 'Missing signal data'
            }), 400
            
        # Validate signal
        if 'ticker' not in signal:
            return jsonify({
                'status': 'error',
                'message': 'Missing ticker in signal'
            }), 400
            
        if 'direction' not in signal:
            return jsonify({
                'status': 'error',
                'message': 'Missing trade direction in signal'
            }), 400
            
        # Execute the trade
        order = options_trader.execute_signal_trade(signal)
        
        if not order:
            return jsonify({
                'status': 'error',
                'message': 'Failed to execute options trade'
            }), 500
            
        return jsonify({
            'status': 'success',
            'data': order
        })
        
    except Exception as e:
        logger.error(f"Error executing options trade: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Error executing options trade: {str(e)}"
        }), 500


def register_options_api(app):
    """
    Register options API routes with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(options_api)
    logger.info("Options API routes registered")