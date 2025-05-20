"""
Account Information API Routes

This module provides API endpoints for account information, including
balance, positions, orders, and portfolio analytics.
"""
import logging
from flask import Blueprint, jsonify, request

from features.account.info import get_account_service

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('account', __name__, url_prefix='/api/account')

@bp.route('/info', methods=['GET'])
def get_account_info():
    """
    Get account information.
    
    Query params:
        force_refresh: Whether to force a refresh (default: false)
    
    Returns:
        JSON with account information
    """
    try:
        # Parse query parameters
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        # Get account service
        account_service = get_account_service()
        
        # Get account information
        account = account_service.get_account(force_refresh)
        
        if not account:
            return jsonify({
                'status': 'error',
                'message': 'Could not retrieve account information'
            }), 500
            
        # Add some derived metrics
        account['buying_power'] = account_service.get_buying_power()
        account['equity'] = account_service.get_equity()
        account['cash'] = account_service.get_cash()
        account['position_value'] = account_service.get_position_value()
        
        return jsonify({
            'status': 'success',
            'account': account
        })
    except Exception as e:
        logger.error(f"Error getting account information: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving account information: {str(e)}'
        }), 500

@bp.route('/positions', methods=['GET'])
def get_positions():
    """
    Get current positions.
    
    Query params:
        force_refresh: Whether to force a refresh (default: false)
        symbol: Filter to a specific symbol (optional)
    
    Returns:
        JSON with positions
    """
    try:
        # Parse query parameters
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        symbol = request.args.get('symbol')
        
        # Get account service
        account_service = get_account_service()
        
        if symbol:
            # Get position for specific symbol
            position = account_service.get_position_by_symbol(symbol)
            
            if not position:
                return jsonify({
                    'status': 'error',
                    'message': f'No position found for {symbol}'
                }), 404
                
            return jsonify({
                'status': 'success',
                'position': position
            })
        else:
            # Get all positions
            positions = account_service.get_positions(force_refresh)
            
            # Add allocation percentages
            portfolio_allocation = account_service.calculate_portfolio_allocation()
            for position in positions:
                symbol = position.get('symbol')
                if symbol in portfolio_allocation:
                    position['allocation_percent'] = portfolio_allocation[symbol]
                
            return jsonify({
                'status': 'success',
                'positions': positions
            })
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving positions: {str(e)}'
        }), 500

@bp.route('/orders', methods=['GET'])
def get_orders():
    """
    Get orders.
    
    Query params:
        status: Order status - 'open', 'closed', or 'all' (default: 'open')
        force_refresh: Whether to force a refresh (default: false)
    
    Returns:
        JSON with orders
    """
    try:
        # Parse query parameters
        status = request.args.get('status', 'open')
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        # Get account service
        account_service = get_account_service()
        
        # Get orders
        orders = account_service.get_orders(status, force_refresh)
        
        return jsonify({
            'status': 'success',
            'orders': orders
        })
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving orders: {str(e)}'
        }), 500

@bp.route('/portfolio/history', methods=['GET'])
def get_portfolio_history():
    """
    Get portfolio value history.
    
    Query params:
        days: Number of days of history (default: 30)
    
    Returns:
        JSON with portfolio history
    """
    try:
        # Parse query parameters
        days = int(request.args.get('days', 30))
        
        # Get account service
        account_service = get_account_service()
        
        # Get portfolio history
        history = account_service.get_portfolio_value_history(days)
        
        return jsonify({
            'status': 'success',
            'history': history
        })
    except Exception as e:
        logger.error(f"Error getting portfolio history: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving portfolio history: {str(e)}'
        }), 500

@bp.route('/risk-metrics', methods=['GET'])
def get_risk_metrics():
    """
    Get risk metrics for the account.
    
    Returns:
        JSON with risk metrics
    """
    try:
        # Get account service
        account_service = get_account_service()
        
        # Get risk metrics
        metrics = account_service.get_risk_metrics()
        
        return jsonify({
            'status': 'success',
            'metrics': metrics
        })
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving risk metrics: {str(e)}'
        }), 500

@bp.route('/activity/today', methods=['GET'])
def get_daily_activity():
    """
    Get today's trading activity.
    
    Returns:
        JSON with activity
    """
    try:
        # Get account service
        account_service = get_account_service()
        
        # Get today's activity
        activity = account_service.get_daily_activity()
        
        return jsonify({
            'status': 'success',
            'activity': activity
        })
    except Exception as e:
        logger.error(f"Error getting daily activity: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving daily activity: {str(e)}'
        }), 500

def register_routes(app):
    """Register account API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Account API routes registered")