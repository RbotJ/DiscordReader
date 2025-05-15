"""
Trade execution module for Alpaca paper trading.

This module handles the execution of trades, including placing orders,
tracking positions, and managing trade lifecycle.
"""
import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime, timedelta, date

from app import app, db
from common.db_models import (
    OrderModel, PositionModel, NotificationModel, 
    SignalModel, OptionsContractModel
)

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.models import Order, Position

# Configure logger
logger = logging.getLogger(__name__)

# Global client
trading_client = None


def initialize_trading_client() -> bool:
    """Initialize Alpaca trading client."""
    global trading_client
    
    api_key = os.environ.get("ALPACA_API_KEY", app.config.get("ALPACA_API_KEY", ""))
    api_secret = os.environ.get("ALPACA_API_SECRET", app.config.get("ALPACA_API_SECRET", ""))
    
    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set")
        return False
    
    try:
        # Initialize Trading client for paper trading
        trading_client = TradingClient(api_key, api_secret, paper=True)
        
        # Check connection by getting account info
        account = trading_client.get_account()
        if account:
            logger.info(f"Trading client initialized successfully. Account ID: {account.id}")
            return True
        else:
            logger.error("Failed to get account info")
            return False
    
    except Exception as e:
        logger.error(f"Failed to initialize trading client: {e}")
        return False


def get_account_info() -> Dict[str, Any]:
    """Get account information from Alpaca."""
    if not trading_client:
        if not initialize_trading_client():
            return {}
    
    try:
        account = trading_client.get_account()
        
        return {
            "id": account.id,
            "status": account.status,
            "currency": account.currency,
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "equity": float(account.equity),
            "last_equity": float(account.last_equity),
            "long_market_value": float(account.long_market_value),
            "short_market_value": float(account.short_market_value),
            "initial_margin": float(account.initial_margin),
            "maintenance_margin": float(account.maintenance_margin),
            "day_trade_count": account.day_trade_count,
            "daytrade_count_limit": account.daytrade_count_limit,
            "daytrading_buying_power": float(account.daytrading_buying_power),
            "regt_buying_power": float(account.regt_buying_power),
            "trading_blocked": account.trading_blocked,
            "transfers_blocked": account.transfers_blocked,
            "account_blocked": account.account_blocked,
            "created_at": account.created_at.isoformat(),
            "trade_suspended_by_user": account.trade_suspended_by_user,
            "multiplier": account.multiplier,
            "shorting_enabled": account.shorting_enabled,
            "pattern_day_trader": account.pattern_day_trader
        }
    
    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        return {}


def place_market_order(
    symbol: str,
    qty: int,
    side: str,
    time_in_force: str = "day",
    extended_hours: bool = False,
    client_order_id: Optional[str] = None,
    signal_id: Optional[int] = None
) -> Optional[str]:
    """Place a market order."""
    if not trading_client:
        if not initialize_trading_client():
            return None
    
    try:
        # Create client order ID if not provided
        if not client_order_id:
            client_order_id = f"market-{uuid.uuid4().hex[:8]}"
        
        # Map side string to OrderSide enum
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Map time_in_force string to TimeInForce enum
        order_tif = TimeInForce.DAY
        if time_in_force.lower() == "gtc":
            order_tif = TimeInForce.GTC
        elif time_in_force.lower() == "ioc":
            order_tif = TimeInForce.IOC
        elif time_in_force.lower() == "fok":
            order_tif = TimeInForce.FOK
        
        # Create order request
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=order_tif,
            client_order_id=client_order_id,
            extended_hours=extended_hours
        )
        
        # Submit order
        order = trading_client.submit_order(order_data)
        
        # Store order in database
        with app.app_context():
            new_order = OrderModel()
            new_order.alpaca_order_id = order.id
            new_order.client_order_id = client_order_id
            new_order.symbol = symbol
            new_order.quantity = qty
            new_order.side = side.lower()
            new_order.type = "market"
            new_order.time_in_force = time_in_force.lower()
            new_order.status = order.status.value
            
            if signal_id:
                new_order.signal_id = signal_id
            
            db.session.add(new_order)
            db.session.commit()
            
            # Create notification
            notification = NotificationModel()
            notification.type = "trade"
            notification.title = f"{side.upper()} {qty} {symbol} Market Order Placed"
            notification.message = f"Order {order.id} to {side.lower()} {qty} shares of {symbol} has been placed."
            notification.meta_data = {
                "order_id": order.id,
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "type": "market",
                "signal_id": signal_id
            }
            notification.read = False
            
            db.session.add(notification)
            db.session.commit()
        
        logger.info(f"Market order placed: {order.id} for {qty} {symbol} {side}")
        return order.id
    
    except Exception as e:
        logger.error(f"Failed to place market order: {e}")
        return None


def place_limit_order(
    symbol: str,
    qty: int,
    side: str,
    limit_price: float,
    time_in_force: str = "day",
    extended_hours: bool = False,
    client_order_id: Optional[str] = None,
    signal_id: Optional[int] = None
) -> Optional[str]:
    """Place a limit order."""
    if not trading_client:
        if not initialize_trading_client():
            return None
    
    try:
        # Create client order ID if not provided
        if not client_order_id:
            client_order_id = f"limit-{uuid.uuid4().hex[:8]}"
        
        # Map side string to OrderSide enum
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Map time_in_force string to TimeInForce enum
        order_tif = TimeInForce.DAY
        if time_in_force.lower() == "gtc":
            order_tif = TimeInForce.GTC
        elif time_in_force.lower() == "ioc":
            order_tif = TimeInForce.IOC
        elif time_in_force.lower() == "fok":
            order_tif = TimeInForce.FOK
        
        # Create order request
        order_data = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            type=OrderType.LIMIT,
            limit_price=limit_price,
            time_in_force=order_tif,
            client_order_id=client_order_id,
            extended_hours=extended_hours
        )
        
        # Submit order
        order = trading_client.submit_order(order_data)
        
        # Store order in database
        with app.app_context():
            new_order = OrderModel()
            new_order.alpaca_order_id = order.id
            new_order.client_order_id = client_order_id
            new_order.symbol = symbol
            new_order.quantity = qty
            new_order.side = side.lower()
            new_order.type = "limit"
            new_order.time_in_force = time_in_force.lower()
            new_order.status = order.status.value
            new_order.limit_price = limit_price
            
            if signal_id:
                new_order.signal_id = signal_id
            
            db.session.add(new_order)
            db.session.commit()
            
            # Create notification
            notification = NotificationModel()
            notification.type = "trade"
            notification.title = f"{side.upper()} {qty} {symbol} Limit Order Placed"
            notification.message = f"Order {order.id} to {side.lower()} {qty} shares of {symbol} at ${limit_price:.2f} has been placed."
            notification.meta_data = {
                "order_id": order.id,
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "type": "limit",
                "limit_price": limit_price,
                "signal_id": signal_id
            }
            notification.read = False
            
            db.session.add(notification)
            db.session.commit()
        
        logger.info(f"Limit order placed: {order.id} for {qty} {symbol} {side} at {limit_price}")
        return order.id
    
    except Exception as e:
        logger.error(f"Failed to place limit order: {e}")
        return None


def place_stop_order(
    symbol: str,
    qty: int,
    side: str,
    stop_price: float,
    time_in_force: str = "day",
    client_order_id: Optional[str] = None,
    signal_id: Optional[int] = None
) -> Optional[str]:
    """Place a stop order."""
    if not trading_client:
        if not initialize_trading_client():
            return None
    
    try:
        # Create client order ID if not provided
        if not client_order_id:
            client_order_id = f"stop-{uuid.uuid4().hex[:8]}"
        
        # Map side string to OrderSide enum
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Map time_in_force string to TimeInForce enum
        order_tif = TimeInForce.DAY
        if time_in_force.lower() == "gtc":
            order_tif = TimeInForce.GTC
        elif time_in_force.lower() == "ioc":
            order_tif = TimeInForce.IOC
        elif time_in_force.lower() == "fok":
            order_tif = TimeInForce.FOK
        
        # Create order request
        order_data = StopOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            type=OrderType.STOP,
            stop_price=stop_price,
            time_in_force=order_tif,
            client_order_id=client_order_id
        )
        
        # Submit order
        order = trading_client.submit_order(order_data)
        
        # Store order in database
        with app.app_context():
            new_order = OrderModel()
            new_order.alpaca_order_id = order.id
            new_order.client_order_id = client_order_id
            new_order.symbol = symbol
            new_order.quantity = qty
            new_order.side = side.lower()
            new_order.type = "stop"
            new_order.time_in_force = time_in_force.lower()
            new_order.status = order.status.value
            new_order.stop_price = stop_price
            
            if signal_id:
                new_order.signal_id = signal_id
            
            db.session.add(new_order)
            db.session.commit()
            
            # Create notification
            notification = NotificationModel()
            notification.type = "trade"
            notification.title = f"{side.upper()} {qty} {symbol} Stop Order Placed"
            notification.message = f"Order {order.id} to {side.lower()} {qty} shares of {symbol} at stop price ${stop_price:.2f} has been placed."
            notification.meta_data = {
                "order_id": order.id,
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "type": "stop",
                "stop_price": stop_price,
                "signal_id": signal_id
            }
            notification.read = False
            
            db.session.add(notification)
            db.session.commit()
        
        logger.info(f"Stop order placed: {order.id} for {qty} {symbol} {side} at {stop_price}")
        return order.id
    
    except Exception as e:
        logger.error(f"Failed to place stop order: {e}")
        return None


def get_order_status(order_id: str) -> Dict[str, Any]:
    """Get the status of an order."""
    if not trading_client:
        if not initialize_trading_client():
            return {}
    
    try:
        order = trading_client.get_order(order_id)
        
        result = {
            "id": order.id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "asset_class": order.asset_class,
            "qty": order.qty,
            "filled_qty": order.filled_qty,
            "filled_avg_price": order.filled_avg_price,
            "order_type": order.order_type.value,
            "side": order.side.value,
            "time_in_force": order.time_in_force.value,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            "expired_at": order.expired_at.isoformat() if order.expired_at else None,
            "canceled_at": order.canceled_at.isoformat() if order.canceled_at else None,
            "extended_hours": order.extended_hours,
            "limit_price": order.limit_price,
            "stop_price": order.stop_price
        }
        
        # Update order in database
        with app.app_context():
            order_model = db.session.query(OrderModel).filter_by(alpaca_order_id=order_id).first()
            
            if order_model:
                order_model.status = order.status.value
                order_model.filled_qty = order.filled_qty
                order_model.filled_avg_price = order.filled_avg_price
                order_model.updated_at = datetime.utcnow()
                
                db.session.commit()
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get order status for {order_id}: {e}")
        return {}


def cancel_order(order_id: str) -> bool:
    """Cancel an open order."""
    if not trading_client:
        if not initialize_trading_client():
            return False
    
    try:
        trading_client.cancel_order_by_id(order_id)
        
        # Update order in database
        with app.app_context():
            order_model = db.session.query(OrderModel).filter_by(alpaca_order_id=order_id).first()
            
            if order_model:
                order_model.status = "canceled"
                order_model.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                # Create notification
                notification = NotificationModel()
                notification.type = "trade"
                notification.title = f"Order Canceled"
                notification.message = f"Order {order_id} for {order_model.symbol} has been canceled."
                notification.meta_data = {
                    "order_id": order_id,
                    "symbol": order_model.symbol,
                    "side": order_model.side,
                    "quantity": order_model.quantity,
                    "type": order_model.type
                }
                notification.read = False
                
                db.session.add(notification)
                db.session.commit()
        
        logger.info(f"Order {order_id} canceled")
        return True
    
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        return False


def get_positions() -> List[Dict[str, Any]]:
    """Get all open positions."""
    if not trading_client:
        if not initialize_trading_client():
            return []
    
    try:
        positions = trading_client.get_all_positions()
        
        result = []
        
        for position in positions:
            pos_dict = {
                "symbol": position.symbol,
                "qty": position.qty,
                "side": "long" if float(position.qty) > 0 else "short", 
                "avg_entry_price": position.avg_entry_price,
                "market_value": position.market_value,
                "cost_basis": position.cost_basis,
                "unrealized_pl": position.unrealized_pl,
                "unrealized_plpc": position.unrealized_plpc,
                "current_price": position.current_price,
                "lastday_price": position.lastday_price,
                "change_today": position.change_today,
                "asset_class": position.asset_class,
                "asset_marginable": position.asset_marginable
            }
            
            result.append(pos_dict)
            
            # Update position in database
            with app.app_context():
                position_model = db.session.query(PositionModel).filter_by(
                    symbol=position.symbol,
                    closed_at=None
                ).first()
                
                if position_model:
                    # Update existing position
                    position_model.quantity = float(position.qty)
                    position_model.avg_entry_price = float(position.avg_entry_price)
                    position_model.side = "long" if float(position.qty) > 0 else "short"
                    position_model.market_value = float(position.market_value)
                    position_model.cost_basis = float(position.cost_basis)
                    position_model.unrealized_pl = float(position.unrealized_pl)
                    position_model.unrealized_plpc = float(position.unrealized_plpc)
                    position_model.current_price = float(position.current_price)
                    position_model.lastday_price = float(position.lastday_price)
                    position_model.change_today = float(position.change_today)
                    position_model.updated_at = datetime.utcnow()
                else:
                    # Create new position
                    new_position = PositionModel()
                    new_position.symbol = position.symbol
                    new_position.quantity = float(position.qty)
                    new_position.avg_entry_price = float(position.avg_entry_price)
                    new_position.side = "long" if float(position.qty) > 0 else "short"
                    new_position.market_value = float(position.market_value)
                    new_position.cost_basis = float(position.cost_basis)
                    new_position.unrealized_pl = float(position.unrealized_pl)
                    new_position.unrealized_plpc = float(position.unrealized_plpc)
                    new_position.current_price = float(position.current_price)
                    new_position.lastday_price = float(position.lastday_price)
                    new_position.change_today = float(position.change_today)
                    
                    db.session.add(new_position)
                
                db.session.commit()
        
        # Check for closed positions
        with app.app_context():
            open_positions = db.session.query(PositionModel).filter_by(closed_at=None).all()
            
            for pos in open_positions:
                # If position not in current positions from Alpaca, mark as closed
                if pos.symbol not in [p["symbol"] for p in result]:
                    pos.closed_at = datetime.utcnow()
                    
                    # Create notification
                    notification = NotificationModel()
                    notification.type = "trade"
                    notification.title = f"Position Closed: {pos.symbol}"
                    notification.message = f"Position in {pos.symbol} has been closed."
                    notification.meta_data = {
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "quantity": pos.quantity,
                        "avg_entry_price": pos.avg_entry_price,
                        "current_price": pos.current_price,
                        "unrealized_pl": pos.unrealized_pl
                    }
                    notification.read = False
                    
                    db.session.add(notification)
            
            db.session.commit()
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return []


def execute_signal_trade(signal_id: int) -> Dict[str, Any]:
    """Execute a trade based on a signal."""
    if not trading_client:
        if not initialize_trading_client():
            return {
                "success": False,
                "message": "Failed to initialize trading client"
            }
    
    try:
        with app.app_context():
            # Get the signal
            signal = db.session.query(SignalModel).filter_by(id=signal_id).first()
            
            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return {
                    "success": False,
                    "message": f"Signal {signal_id} not found"
                }
            
            # Get ticker setup
            ticker_setup = signal.ticker_setup
            if not ticker_setup:
                logger.warning(f"Ticker setup for signal {signal_id} not found")
                return {
                    "success": False,
                    "message": f"Ticker setup for signal {signal_id} not found"
                }
            
            symbol = ticker_setup.symbol
            
            # Determine trade direction based on signal category
            side = "buy" if signal.category in ["breakout", "bounce"] else "sell"
            
            # Default quantity
            qty = 10  # Default, should be calculated based on account size, risk, etc.
            
            # Get account info
            account = get_account_info()
            
            if account:
                # Calculate quantity based on a percentage of buying power
                # 2% of buying power per trade
                risk_percent = 0.02
                buying_power = account.get("buying_power", 0)
                
                # Get current price from position if available
                positions = get_positions()
                current_price = None
                
                for pos in positions:
                    if pos["symbol"] == symbol:
                        current_price = float(pos["current_price"])
                        break
                
                # If no position, use a default price or fetch from market data
                if not current_price:
                    current_price = 100  # Default placeholder, should fetch real price
                
                # Calculate quantity
                if current_price > 0:
                    max_trade_amount = buying_power * risk_percent
                    qty = int(max_trade_amount / current_price)
                    
                    # Ensure minimum quantity
                    qty = max(1, qty)
            
            # Adjust for short positions
            if side == "sell":
                # Check if we have the position to sell
                has_position = False
                for pos in get_positions():
                    if pos["symbol"] == symbol and pos["side"] == "long":
                        has_position = True
                        qty = min(qty, int(float(pos["qty"])))
                        break
                
                if not has_position:
                    logger.warning(f"No position to sell for signal {signal_id}")
                    return {
                        "success": False,
                        "message": f"No position to sell for signal {signal_id}"
                    }
            
            # Place market order
            order_id = place_market_order(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force="day",
                signal_id=signal_id
            )
            
            if order_id:
                return {
                    "success": True,
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": qty,
                    "signal_id": signal_id
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to place order"
                }
    
    except Exception as e:
        logger.error(f"Failed to execute signal trade for signal {signal_id}: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


def get_orders(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get orders, with optional filtering by status."""
    if not trading_client:
        if not initialize_trading_client():
            return []
    
    try:
        orders = []
        
        if status:
            # Convert status string to enum
            status_map = {
                "open": "open",
                "closed": "closed",
                "all": "all"
            }
            status_arg = status_map.get(status.lower(), "all")
            
            # Get orders from Alpaca
            orders = trading_client.get_orders(status=status_arg, limit=limit)
        else:
            # Get all orders
            orders = trading_client.get_orders(limit=limit)
        
        # Convert to dictionary format
        result = []
        
        for order in orders:
            order_dict = {
                "id": order.id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "asset_class": order.asset_class,
                "qty": order.qty,
                "filled_qty": order.filled_qty,
                "filled_avg_price": order.filled_avg_price,
                "order_type": order.order_type.value,
                "side": order.side.value,
                "time_in_force": order.time_in_force.value,
                "status": order.status.value,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "expired_at": order.expired_at.isoformat() if order.expired_at else None,
                "canceled_at": order.canceled_at.isoformat() if order.canceled_at else None,
                "extended_hours": order.extended_hours,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price
            }
            
            result.append(order_dict)
            
            # Update order in database
            with app.app_context():
                order_model = db.session.query(OrderModel).filter_by(alpaca_order_id=order.id).first()
                
                if order_model:
                    # Update existing order
                    order_model.status = order.status.value
                    order_model.filled_qty = order.filled_qty
                    order_model.filled_avg_price = order.filled_avg_price
                    order_model.updated_at = datetime.utcnow()
                else:
                    # Create new order record
                    new_order = OrderModel()
                    new_order.alpaca_order_id = order.id
                    new_order.client_order_id = order.client_order_id
                    new_order.symbol = order.symbol
                    new_order.quantity = order.qty
                    new_order.side = order.side.value
                    new_order.type = order.order_type.value
                    new_order.time_in_force = order.time_in_force.value
                    new_order.status = order.status.value
                    new_order.filled_qty = order.filled_qty
                    new_order.filled_avg_price = order.filled_avg_price
                    new_order.limit_price = order.limit_price
                    new_order.stop_price = order.stop_price
                    
                    db.session.add(new_order)
                
                db.session.commit()
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        return []


# Create blueprint for API routes
from flask import Blueprint, request, jsonify
execution_routes = Blueprint('execution', __name__)

@execution_routes.route('/api/execution/account', methods=['GET'])
def account_info_api():
    """Get account information."""
    account = get_account_info()
    return jsonify(account)

@execution_routes.route('/api/execution/positions', methods=['GET'])
def positions_api():
    """Get all open positions."""
    positions = get_positions()
    return jsonify(positions)

@execution_routes.route('/api/execution/orders', methods=['GET'])
def orders_api():
    """Get orders, with optional filtering by status."""
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    
    orders = get_orders(status, limit)
    return jsonify(orders)

@execution_routes.route('/api/execution/order/<order_id>', methods=['GET'])
def order_status_api(order_id):
    """Get the status of an order."""
    order = get_order_status(order_id)
    
    if not order:
        return jsonify({
            "error": f"Order {order_id} not found"
        }), 404
    
    return jsonify(order)

@execution_routes.route('/api/execution/order/<order_id>', methods=['DELETE'])
def cancel_order_api(order_id):
    """Cancel an open order."""
    success = cancel_order(order_id)
    
    if success:
        return jsonify({
            "success": True,
            "message": f"Order {order_id} canceled"
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Failed to cancel order {order_id}"
        }), 400

@execution_routes.route('/api/execution/execute', methods=['POST'])
def execute_trade_api():
    """Execute a trade based on a signal."""
    if not request.is_json:
        return jsonify({
            "error": "Request must be JSON"
        }), 400
    
    data = request.get_json()
    signal_id = data.get('signal_id')
    
    if not signal_id:
        return jsonify({
            "error": "Signal ID is required"
        }), 400
    
    result = execute_signal_trade(signal_id)
    
    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400

@execution_routes.route('/api/execution/order', methods=['POST'])
def place_order_api():
    """Place an order."""
    if not request.is_json:
        return jsonify({
            "error": "Request must be JSON"
        }), 400
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['symbol', 'qty', 'side', 'type']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    # Extract fields
    symbol = data.get('symbol').upper()
    qty = int(data.get('qty'))
    side = data.get('side').lower()
    order_type = data.get('type').lower()
    time_in_force = data.get('time_in_force', 'day').lower()
    extended_hours = data.get('extended_hours', False)
    signal_id = data.get('signal_id')
    
    # Check side
    if side not in ['buy', 'sell']:
        return jsonify({
            "error": "Side must be 'buy' or 'sell'"
        }), 400
    
    # Check type
    if order_type not in ['market', 'limit', 'stop']:
        return jsonify({
            "error": "Type must be 'market', 'limit', or 'stop'"
        }), 400
    
    # Place order based on type
    order_id = None
    
    if order_type == 'market':
        order_id = place_market_order(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=time_in_force,
            extended_hours=extended_hours,
            signal_id=signal_id
        )
    elif order_type == 'limit':
        limit_price = data.get('limit_price')
        
        if not limit_price:
            return jsonify({
                "error": "Limit price is required for limit orders"
            }), 400
        
        order_id = place_limit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            limit_price=float(limit_price),
            time_in_force=time_in_force,
            extended_hours=extended_hours,
            signal_id=signal_id
        )
    elif order_type == 'stop':
        stop_price = data.get('stop_price')
        
        if not stop_price:
            return jsonify({
                "error": "Stop price is required for stop orders"
            }), 400
        
        order_id = place_stop_order(
            symbol=symbol,
            qty=qty,
            side=side,
            stop_price=float(stop_price),
            time_in_force=time_in_force,
            signal_id=signal_id
        )
    
    if order_id:
        return jsonify({
            "success": True,
            "order_id": order_id,
            "message": f"{order_type.capitalize()} order placed for {qty} {symbol} {side}"
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Failed to place {order_type} order"
        }), 400