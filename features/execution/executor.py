import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import alpaca_trade_api as tradeapi

from common.models import Order, OrderSide, OrderType, TimeInForce
from common.utils import publish_event, load_config

# Configure logging
logger = logging.getLogger(__name__)

# In-memory order tracking
_orders: Dict[str, Dict[str, Any]] = {}
_execution_status = "ready"

def submit_order(
    symbol: str,
    quantity: float,
    side: str,
    option_symbol: Optional[str] = None,
    order_type: str = "market",
    time_in_force: str = "day",
    limit_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Submit an order to Alpaca paper trading
    
    Args:
        symbol: Underlying symbol
        quantity: Order quantity
        side: 'buy' or 'sell'
        option_symbol: Optional option symbol (if trading options)
        order_type: 'market', 'limit', 'stop', 'stop_limit'
        time_in_force: 'day', 'gtc', 'ioc', 'fok'
        limit_price: Limit price (required for limit and stop_limit orders)
    
    Returns:
        Dictionary with order details and status
    """
    global _execution_status
    
    try:
        # Load config
        config = load_config()
        
        # Initialize Alpaca API
        api = tradeapi.REST(
            key_id=config['alpaca']['api_key'],
            secret_key=config['alpaca']['api_secret'],
            base_url=config['alpaca']['base_url'],
            api_version='v2'
        )
        
        # Generate a client order ID
        client_order_id = str(uuid.uuid4())
        
        # Set execution status
        _execution_status = "executing"
        
        # Create order parameters
        order_params = {
            "symbol": option_symbol if option_symbol else symbol,
            "qty": quantity,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "client_order_id": client_order_id
        }
        
        # Add limit price if needed
        if order_type in ["limit", "stop_limit"] and limit_price is not None:
            order_params["limit_price"] = limit_price
        
        # Submit the order
        logger.info(f"Submitting order: {order_params}")
        
        # Submit to Alpaca
        try:
            alpaca_order = api.submit_order(**order_params)
            order_id = alpaca_order.id
            
            # Store order details
            _orders[client_order_id] = {
                "id": order_id,
                "client_order_id": client_order_id,
                "symbol": symbol,
                "option_symbol": option_symbol,
                "quantity": quantity,
                "side": side,
                "type": order_type,
                "time_in_force": time_in_force,
                "limit_price": limit_price,
                "status": alpaca_order.status,
                "created_at": datetime.now().isoformat(),
                "filled_at": None,
                "filled_qty": 0,
                "filled_price": 0
            }
            
            # Publish order event
            publish_event("execution.order_submitted", {
                "client_order_id": client_order_id,
                "order_id": order_id,
                "symbol": symbol,
                "option_symbol": option_symbol,
                "side": side,
                "quantity": quantity,
                "status": alpaca_order.status
            })
            
            # Set execution status back to ready
            _execution_status = "ready"
            
            return {
                "client_order_id": client_order_id,
                "order_id": order_id,
                "status": alpaca_order.status
            }
            
        except Exception as e:
            logger.error(f"Alpaca order submission failed: {str(e)}")
            
            # For testing/development, simulate order
            if "API_KEY" not in config['alpaca'] or not config['alpaca']['api_key']:
                logger.warning("Using simulated order execution (DEVELOPMENT ONLY)")
                
                order_id = f"sim-{client_order_id[:8]}"
                
                # Store simulated order
                _orders[client_order_id] = {
                    "id": order_id,
                    "client_order_id": client_order_id,
                    "symbol": symbol,
                    "option_symbol": option_symbol,
                    "quantity": quantity,
                    "side": side,
                    "type": order_type,
                    "time_in_force": time_in_force,
                    "limit_price": limit_price,
                    "status": "filled",  # Simulate immediate fill
                    "created_at": datetime.now().isoformat(),
                    "filled_at": datetime.now().isoformat(),
                    "filled_qty": quantity,
                    "filled_price": limit_price if limit_price else 0
                }
                
                # Publish simulated order events
                publish_event("execution.order_submitted", {
                    "client_order_id": client_order_id,
                    "order_id": order_id,
                    "symbol": symbol,
                    "option_symbol": option_symbol,
                    "side": side,
                    "quantity": quantity,
                    "status": "filled",
                    "simulated": True
                })
                
                publish_event("execution.order_filled", {
                    "client_order_id": client_order_id,
                    "order_id": order_id,
                    "symbol": symbol,
                    "option_symbol": option_symbol,
                    "side": side,
                    "quantity": quantity,
                    "filled_price": limit_price if limit_price else 0,
                    "simulated": True
                })
                
                # Set execution status back to ready
                _execution_status = "ready"
                
                return {
                    "client_order_id": client_order_id,
                    "order_id": order_id,
                    "status": "filled",
                    "simulated": True
                }
            else:
                # Real API error
                _execution_status = "error"
                raise e
    
    except Exception as e:
        logger.error(f"Error submitting order: {str(e)}")
        
        # Set execution status to error
        _execution_status = "error"
        
        # Publish error event
        publish_event("execution.order_error", {
            "symbol": symbol,
            "option_symbol": option_symbol,
            "side": side,
            "quantity": quantity,
            "error": str(e)
        })
        
        raise e

def cancel_order(client_order_id: str) -> bool:
    """
    Cancel an existing order
    
    Args:
        client_order_id: Client order ID to cancel
    
    Returns:
        True if cancellation was successful
    """
    try:
        # Check if order exists
        if client_order_id not in _orders:
            logger.error(f"Order {client_order_id} not found")
            return False
        
        # Get order details
        order = _orders[client_order_id]
        
        # Load config
        config = load_config()
        
        # Initialize Alpaca API
        api = tradeapi.REST(
            key_id=config['alpaca']['api_key'],
            secret_key=config['alpaca']['api_secret'],
            base_url=config['alpaca']['base_url'],
            api_version='v2'
        )
        
        # Cancel the order
        try:
            api.cancel_order(order["id"])
            
            # Update status
            _orders[client_order_id]["status"] = "canceled"
            
            # Publish cancel event
            publish_event("execution.order_canceled", {
                "client_order_id": client_order_id,
                "order_id": order["id"],
                "symbol": order["symbol"],
                "option_symbol": order.get("option_symbol")
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Alpaca order cancellation failed: {str(e)}")
            
            # For testing/development, simulate cancellation
            if "API_KEY" not in config['alpaca'] or not config['alpaca']['api_key']:
                logger.warning("Using simulated order cancellation (DEVELOPMENT ONLY)")
                
                # Update simulated order
                _orders[client_order_id]["status"] = "canceled"
                
                # Publish simulated cancel event
                publish_event("execution.order_canceled", {
                    "client_order_id": client_order_id,
                    "order_id": order["id"],
                    "symbol": order["symbol"],
                    "option_symbol": order.get("option_symbol"),
                    "simulated": True
                })
                
                return True
            else:
                # Real API error
                raise e
    
    except Exception as e:
        logger.error(f"Error canceling order: {str(e)}")
        return False

def get_order(client_order_id: str) -> Optional[Dict[str, Any]]:
    """
    Get order details by client order ID
    
    Args:
        client_order_id: Client order ID
    
    Returns:
        Order details dictionary or None if not found
    """
    try:
        # Check if order exists locally
        if client_order_id in _orders:
            return _orders[client_order_id]
        
        # Not found locally, try to fetch from Alpaca
        config = load_config()
        
        # Initialize Alpaca API
        api = tradeapi.REST(
            key_id=config['alpaca']['api_key'],
            secret_key=config['alpaca']['api_secret'],
            base_url=config['alpaca']['base_url'],
            api_version='v2'
        )
        
        # Get the order from Alpaca
        try:
            alpaca_order = api.get_order_by_client_order_id(client_order_id)
            
            # Create order dictionary
            order = {
                "id": alpaca_order.id,
                "client_order_id": client_order_id,
                "symbol": alpaca_order.symbol,
                "option_symbol": alpaca_order.symbol if "O:" in alpaca_order.symbol else None,
                "quantity": float(alpaca_order.qty),
                "side": alpaca_order.side,
                "type": alpaca_order.type,
                "time_in_force": alpaca_order.time_in_force,
                "limit_price": float(alpaca_order.limit_price) if hasattr(alpaca_order, 'limit_price') else None,
                "status": alpaca_order.status,
                "created_at": alpaca_order.created_at,
                "filled_at": alpaca_order.filled_at,
                "filled_qty": float(alpaca_order.filled_qty) if hasattr(alpaca_order, 'filled_qty') else 0,
                "filled_price": float(alpaca_order.filled_avg_price) if hasattr(alpaca_order, 'filled_avg_price') else 0
            }
            
            # Store locally
            _orders[client_order_id] = order
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to get order from Alpaca: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        return None

def get_all_orders() -> List[Dict[str, Any]]:
    """
    Get all tracked orders
    
    Returns:
        List of order dictionaries
    """
    return list(_orders.values())

def get_trade_execution_status() -> str:
    """
    Get the current execution system status
    
    Returns:
        Status string: 'ready', 'executing', 'error'
    """
    return _execution_status
