"""
Order Execution Service Layer

Centralized service for order execution operations, providing a clean interface
for trade execution, order management, and risk assessment without exposing
implementation details to API routes.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from features.execution.executor import get_order_executor
from common.events.publisher import publish_event

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderRequest:
    """Order request data."""
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    properties: Optional[Dict[str, Any]] = None


@dataclass
class OrderResult:
    """Order execution result."""
    order_id: str
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    filled_quantity: int
    average_fill_price: Optional[float]
    created_at: datetime
    updated_at: datetime
    properties: Optional[Dict[str, Any]] = None


@dataclass
class RiskCheckResult:
    """Risk assessment result."""
    approved: bool
    risk_percent: float
    max_allowed_percent: float
    reason: Optional[str] = None


class ExecutionService:
    """Service for order execution operations."""
    
    def __init__(self):
        self.executor = None
        
    def _get_executor(self):
        """Lazy load order executor."""
        if not self.executor:
            self.executor = get_order_executor()
        return self.executor
    
    def check_position_risk(self, symbol: str, quantity: int, 
                          price: float, max_risk_percent: float = 5.0) -> RiskCheckResult:
        """
        Check if a position meets risk management criteria.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            max_risk_percent: Maximum risk as percentage of portfolio
            
        Returns:
            RiskCheckResult with approval status and details
        """
        try:
            executor = self._get_executor()
            
            # Calculate position value
            position_value = quantity * price
            
            # Get current portfolio value (this would come from account service)
            # For now, we'll use a basic risk check through the executor
            risk_approved = executor.check_position_risk(symbol, quantity, price, max_risk_percent)
            
            # Calculate actual risk percentage (simplified)
            # In a real implementation, this would involve portfolio value calculation
            estimated_risk = min(max_risk_percent, position_value / 100000 * 100)  # Assume $100k portfolio
            
            result = RiskCheckResult(
                approved=risk_approved,
                risk_percent=estimated_risk,
                max_allowed_percent=max_risk_percent,
                reason=None if risk_approved else f"Position exceeds {max_risk_percent}% risk limit"
            )
            
            # Publish risk check event
            publish_event(
                event_type='execution.risk.checked',
                data={
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'approved': risk_approved,
                    'risk_percent': estimated_risk,
                    'timestamp': datetime.now().isoformat()
                },
                channel='execution:risk',
                source='execution_service'
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking position risk for {symbol}: {e}")
            return RiskCheckResult(
                approved=False,
                risk_percent=0.0,
                max_allowed_percent=max_risk_percent,
                reason=f"Risk check failed: {str(e)}"
            )
    
    def execute_market_order(self, order_request: OrderRequest, correlation_id: Optional[str] = None) -> Optional[OrderResult]:
        """
        Execute a market order.
        
        Args:
            order_request: Order request details
            
        Returns:
            OrderResult or None if execution failed
        """
        try:
            executor = self._get_executor()
            
            # Execute the order
            order_data = executor.execute_market_order(
                order_request.symbol,
                order_request.quantity,
                order_request.side.value,
                order_request.properties or {}
            )
            
            if not order_data:
                logger.error(f"Market order execution failed for {order_request.symbol}")
                return None
            
            # Convert to OrderResult
            result = OrderResult(
                order_id=order_data.get('id', ''),
                symbol=order_request.symbol.upper(),
                quantity=order_request.quantity,
                side=order_request.side,
                order_type=OrderType.MARKET,
                status=OrderStatus(order_data.get('status', 'pending')),
                filled_quantity=order_data.get('filled_qty', 0),
                average_fill_price=order_data.get('filled_avg_price'),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                properties=order_request.properties
            )
            
            # Publish execution event
            publish_event(
                event_type='execution.order.executed',
                data={
                    'order_id': result.order_id,
                    'symbol': result.symbol,
                    'quantity': result.quantity,
                    'side': result.side.value,
                    'order_type': 'market',
                    'status': result.status.value,
                    'timestamp': result.created_at.isoformat()
                },
                channel='execution:orders',
                source='execution_service',
                correlation_id=correlation_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing market order for {order_request.symbol}: {e}")
            return None
    
    def execute_limit_order(self, order_request: OrderRequest, correlation_id: Optional[str] = None) -> Optional[OrderResult]:
        """
        Execute a limit order.
        
        Args:
            order_request: Order request details (must include limit_price)
            
        Returns:
            OrderResult or None if execution failed
        """
        try:
            if not order_request.limit_price:
                logger.error("Limit price required for limit order")
                return None
                
            executor = self._get_executor()
            
            # Execute the order
            order_data = executor.execute_limit_order(
                order_request.symbol,
                order_request.quantity,
                order_request.side.value,
                order_request.limit_price,
                order_request.time_in_force,
                order_request.properties or {}
            )
            
            if not order_data:
                logger.error(f"Limit order execution failed for {order_request.symbol}")
                return None
            
            # Convert to OrderResult
            result = OrderResult(
                order_id=order_data.get('id', ''),
                symbol=order_request.symbol.upper(),
                quantity=order_request.quantity,
                side=order_request.side,
                order_type=OrderType.LIMIT,
                status=OrderStatus(order_data.get('status', 'pending')),
                filled_quantity=order_data.get('filled_qty', 0),
                average_fill_price=order_data.get('filled_avg_price'),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                properties=order_request.properties
            )
            
            # Publish execution event
            publish_event(
                event_type='execution.order.executed',
                data={
                    'order_id': result.order_id,
                    'symbol': result.symbol,
                    'quantity': result.quantity,
                    'side': result.side.value,
                    'order_type': 'limit',
                    'limit_price': order_request.limit_price,
                    'status': result.status.value,
                    'timestamp': result.created_at.isoformat()
                },
                channel='execution:orders',
                source='execution_service',
                correlation_id=correlation_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing limit order for {order_request.symbol}: {e}")
            return None
    
    def cancel_order(self, order_id: str, correlation_id: Optional[str] = None) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancellation successful
        """
        try:
            executor = self._get_executor()
            success = executor.cancel_order(order_id)
            
            if success:
                publish_event(
                    event_type='execution.order.cancelled',
                    data={
                        'order_id': order_id,
                        'timestamp': datetime.now().isoformat()
                    },
                    channel='execution:orders',
                    source='execution_service',
                    correlation_id=correlation_id
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """
        Get the current status of an order.
        
        Args:
            order_id: Order ID to check
            
        Returns:
            OrderResult or None if not found
        """
        try:
            executor = self._get_executor()
            order_data = executor.get_order(order_id)
            
            if not order_data:
                return None
            
            # Convert to OrderResult
            result = OrderResult(
                order_id=order_data.get('id', ''),
                symbol=order_data.get('symbol', '').upper(),
                quantity=order_data.get('qty', 0),
                side=OrderSide(order_data.get('side', 'buy')),
                order_type=OrderType(order_data.get('order_type', 'market')),
                status=OrderStatus(order_data.get('status', 'pending')),
                filled_quantity=order_data.get('filled_qty', 0),
                average_fill_price=order_data.get('filled_avg_price'),
                created_at=datetime.fromisoformat(order_data.get('created_at', datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(order_data.get('updated_at', datetime.now().isoformat()))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """
        Get all open orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of OrderResult
        """
        try:
            executor = self._get_executor()
            orders_data = executor.get_orders(status='open', symbol=symbol)
            
            if not orders_data:
                return []
            
            orders = []
            for order_data in orders_data:
                result = OrderResult(
                    order_id=order_data.get('id', ''),
                    symbol=order_data.get('symbol', '').upper(),
                    quantity=order_data.get('qty', 0),
                    side=OrderSide(order_data.get('side', 'buy')),
                    order_type=OrderType(order_data.get('order_type', 'market')),
                    status=OrderStatus(order_data.get('status', 'pending')),
                    filled_quantity=order_data.get('filled_qty', 0),
                    average_fill_price=order_data.get('filled_avg_price'),
                    created_at=datetime.fromisoformat(order_data.get('created_at', datetime.now().isoformat())),
                    updated_at=datetime.fromisoformat(order_data.get('updated_at', datetime.now().isoformat()))
                )
                orders.append(result)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []


# Global service instance
_execution_service = None


def get_execution_service() -> ExecutionService:
    """Get the execution service instance."""
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService()
    return _execution_service