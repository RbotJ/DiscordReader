"""
Order Request Classes

This module provides custom order request classes that might not be available in the 
current version of the Alpaca SDK.
"""
from typing import Dict, Optional, Union
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce

class MarketOrderRequest:
    """Market order request class."""
    
    def __init__(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False,
        client_order_id: Optional[str] = None
    ):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.type = OrderType.MARKET
        self.time_in_force = time_in_force
        self.extended_hours = extended_hours
        self.client_order_id = client_order_id
        
class LimitOrderRequest:
    """Limit order request class."""
    
    def __init__(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        limit_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False,
        client_order_id: Optional[str] = None
    ):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.type = OrderType.LIMIT
        self.limit_price = limit_price
        self.time_in_force = time_in_force
        self.extended_hours = extended_hours
        self.client_order_id = client_order_id
        
class StopOrderRequest:
    """Stop order request class."""
    
    def __init__(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        stop_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False,
        client_order_id: Optional[str] = None
    ):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.type = OrderType.STOP
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.extended_hours = extended_hours
        self.client_order_id = client_order_id
        
class StopLimitOrderRequest:
    """Stop limit order request class."""
    
    def __init__(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        stop_price: float,
        limit_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False,
        client_order_id: Optional[str] = None
    ):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.type = OrderType.STOP_LIMIT
        self.stop_price = stop_price
        self.limit_price = limit_price
        self.time_in_force = time_in_force
        self.extended_hours = extended_hours
        self.client_order_id = client_order_id
        
class BracketOrderRequest:
    """Bracket order request class."""
    
    def __init__(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None,
        take_profit: Optional[Dict[str, float]] = None,
        stop_loss: Optional[Dict[str, float]] = None,
        extended_hours: bool = False,
        client_order_id: Optional[str] = None
    ):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.type = type
        self.time_in_force = time_in_force
        self.limit_price = limit_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.extended_hours = extended_hours
        self.client_order_id = client_order_id