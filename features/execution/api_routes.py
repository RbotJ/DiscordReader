"""
Order Execution API Routes

This module provides API endpoints for trade execution, including
order placement, management, and status tracking.
"""
import logging
from flask import Blueprint, jsonify, request

from features.execution.service import get_execution_service, OrderRequest, OrderSide, OrderType

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('execution', __name__, url_prefix='/api/execution')

def register_routes(app):
    """Register execution routes with the Flask app"""
    app.register_blueprint(bp)
    logger.info("Execution API routes registered")

@bp.route('/market-order', methods=['POST'])
def execute_market_order():
    """
    Execute a market order.
    
    Expected JSON payload:
        {
            "symbol": "SPY",
            "quantity": 1,
            "side": "buy" or "sell",
            "properties": {} (optional)
        }
        
    Returns:
        JSON with order details
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
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        side = data.get('side')
        properties = data.get('properties')
        
        # Validate required parameters
        if not symbol or not quantity or not side:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters: symbol, quantity, and side'
            }), 400
            
        # Validate side
        if side not in ['buy', 'sell']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid side: must be "buy" or "sell"'
            }), 400
            
        # Get execution service
        execution_service = get_execution_service()
        from uuid import uuid4
        correlation_id = data.get('correlation_id') or str(uuid4())
        
        # Check position risk if provided
        price = data.get('price')
        max_risk = data.get('max_risk_percent', 5.0)
        
        if price and max_risk:
            risk_result = execution_service.check_position_risk(symbol, quantity, price, max_risk)
            if not risk_result.approved:
                return jsonify({
                    'status': 'error',
                    'message': risk_result.reason or f'Order exceeds maximum risk ({max_risk}%)'
                }), 400
        
        # Create order request
        order_request = OrderRequest(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide(side),
            order_type=OrderType.MARKET,
            properties=properties
        )
                
        # Execute order
        order = execution_service.execute_market_order(order_request, correlation_id=correlation_id)
        
        if not order:
            return jsonify({
                'status': 'error',
                'message': f'Failed to execute market order for {symbol}'
            }), 500
            
        return jsonify({
            'status': 'success',
            'message': f'Market {side} order executed for {quantity} {symbol}',
            'order': {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'quantity': order.quantity,
                'side': order.side.value,
                'status': order.status.value,
                'filled_quantity': order.filled_quantity,
                'average_fill_price': float(order.average_fill_price) if order.average_fill_price else None
            }
        })
    except Exception as e:
        logger.error(f"Error executing market order: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error executing market order: {str(e)}'
        }), 500

@bp.route('/limit-order', methods=['POST'])
def execute_limit_order():
    """
    Execute a limit order.
    
    Expected JSON payload:
        {
            "symbol": "SPY",
            "quantity": 1,
            "side": "buy" or "sell",
            "limit_price": 123.45,
            "time_in_force": "day" (optional, default: "day"),
            "properties": {} (optional)
        }
        
    Returns:
        JSON with order details
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
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        side = data.get('side')
        limit_price = data.get('limit_price')
        time_in_force = data.get('time_in_force', 'day')
        properties = data.get('properties')
        
        # Validate required parameters
        if not symbol or not quantity or not side or not limit_price:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters: symbol, quantity, side, and limit_price'
            }), 400
            
        # Validate side
        if side not in ['buy', 'sell']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid side: must be "buy" or "sell"'
            }), 400
            
        # Get order executor
        executor = get_order_executor()
        
        # Check position risk
        max_risk = data.get('max_risk_percent', 5.0)
        risk_ok = executor.check_position_risk(symbol, quantity, limit_price, max_risk)
        if not risk_ok:
            return jsonify({
                'status': 'error',
                'message': f'Order exceeds maximum risk ({max_risk}%)'
            }), 400
                
        # Execute order
        order = executor.execute_limit_order(
            symbol, quantity, side, limit_price, time_in_force, properties
        )
        
        if not order:
            return jsonify({
                'status': 'error',
                'message': f'Failed to execute limit order for {symbol}'
            }), 500
            
        return jsonify({
            'status': 'success',
            'message': f'Limit {side} order executed for {quantity} {symbol} @ {limit_price}',
            'order': order
        })
    except Exception as e:
        logger.error(f"Error executing limit order: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error executing limit order: {str(e)}'
        }), 500

@bp.route('/bracket-order', methods=['POST'])
def execute_bracket_order():
    """
    Execute a bracket order (entry with take profit and stop loss).
    
    Expected JSON payload:
        {
            "symbol": "SPY",
            "quantity": 1,
            "side": "buy" or "sell",
            "entry_price": 123.45 (optional, market order if not provided),
            "take_profit_price": 125.45 (optional),
            "stop_loss_price": 121.45 (optional),
            "properties": {} (optional)
        }
        
    Returns:
        JSON with order details
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
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        side = data.get('side')
        entry_price = data.get('entry_price')
        take_profit_price = data.get('take_profit_price')
        stop_loss_price = data.get('stop_loss_price')
        properties = data.get('properties')
        
        # Validate required parameters
        if not symbol or not quantity or not side:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters: symbol, quantity, and side'
            }), 400
            
        # Validate side
        if side not in ['buy', 'sell']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid side: must be "buy" or "sell"'
            }), 400
            
        # Get order executor
        executor = get_order_executor()
        
        # Check position risk
        price = entry_price or data.get('price')
        if price:
            max_risk = data.get('max_risk_percent', 5.0)
            risk_ok = executor.check_position_risk(symbol, quantity, price, max_risk)
            if not risk_ok:
                return jsonify({
                    'status': 'error',
                    'message': f'Order exceeds maximum risk ({max_risk}%)'
                }), 400
                
        # Execute order
        order = executor.execute_bracket_order(
            symbol, quantity, side, entry_price, take_profit_price, stop_loss_price, properties
        )
        
        if not order:
            return jsonify({
                'status': 'error',
                'message': f'Failed to execute bracket order for {symbol}'
            }), 500
            
        return jsonify({
            'status': 'success',
            'message': f'Bracket {side} order executed for {quantity} {symbol}',
            'order': order
        })
    except Exception as e:
        logger.error(f"Error executing bracket order: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error executing bracket order: {str(e)}'
        }), 500

@bp.route('/option-order', methods=['POST'])
def execute_option_order():
    """
    Execute an option order.
    
    Expected JSON payload:
        {
            "option_symbol": "SPY230515C450000",
            "quantity": 1,
            "side": "buy" or "sell",
            "price_type": "market" or "limit" (optional, default: "market"),
            "limit_price": 1.25 (required for limit orders),
            "properties": {} (optional)
        }
        
    Returns:
        JSON with order details
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
        option_symbol = data.get('option_symbol')
        quantity = data.get('quantity')
        side = data.get('side')
        price_type = data.get('price_type', 'market')
        limit_price = data.get('limit_price')
        properties = data.get('properties')
        
        # Validate required parameters
        if not option_symbol or not quantity or not side:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters: option_symbol, quantity, and side'
            }), 400
            
        # Validate side
        if side not in ['buy', 'sell']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid side: must be "buy" or "sell"'
            }), 400
            
        # Validate price type and limit price
        if price_type not in ['market', 'limit']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid price_type: must be "market" or "limit"'
            }), 400
            
        if price_type == 'limit' and not limit_price:
            return jsonify({
                'status': 'error',
                'message': 'limit_price is required for limit orders'
            }), 400
            
        # Get order executor
        executor = get_order_executor()
        
        # Check position risk for limit orders
        if price_type == 'limit':
            max_risk = data.get('max_risk_percent', 5.0)
            risk_ok = executor.check_position_risk(option_symbol, quantity, limit_price, max_risk)
            if not risk_ok:
                return jsonify({
                    'status': 'error',
                    'message': f'Order exceeds maximum risk ({max_risk}%)'
                }), 400
                
        # Execute order
        order = executor.execute_option_order(
            option_symbol, quantity, side, price_type, limit_price, properties
        )
        
        if not order:
            return jsonify({
                'status': 'error',
                'message': f'Failed to execute option order for {option_symbol}'
            }), 500
            
        return jsonify({
            'status': 'success',
            'message': f'{price_type.capitalize()} {side} order executed for {quantity} {option_symbol}',
            'order': order
        })
    except Exception as e:
        logger.error(f"Error executing option order: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error executing option order: {str(e)}'
        }), 500

@bp.route('/cancel/<order_id>', methods=['DELETE'])
def cancel_order(order_id):
    """
    Cancel a pending order.
    
    Returns:
        JSON with cancellation status
    """
    try:
        # Get order executor
        executor = get_order_executor()
        
        # Cancel order
        result = executor.cancel_pending_order(order_id)
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'Failed to cancel order {order_id}'
            }), 500
            
        return jsonify({
            'status': 'success',
            'message': f'Order {order_id} canceled successfully'
        })
    except Exception as e:
        logger.error(f"Error canceling order {order_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error canceling order: {str(e)}'
        }), 500

