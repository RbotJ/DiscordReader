"""
Position Manager Module

This module handles tracking and management of options positions.
It provides functionality for position sizing, tracking P&L, and
managing portfolio exposure.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union, Tuple, TypeVar, cast, Type
from alpaca.trading.models import Position
from alpaca.common.types import RawData
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.orm.attributes import set_attribute
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.sql.schema import Column
from datetime import datetime, timedelta
import time
import math
import threading
from decimal import Decimal

from app import app, db
from common.db_models import (
    PositionModel, OrderModel, SignalModel, NotificationModel,
    OptionsContractModel, MarketDataModel
)
from common.events import EventChannels
from common.db import db, publish_event
from common.db_models import PositionModel

# Type variable for SQLAlchemy model instance
Model = TypeVar('Model')

# Set up logger
logger = logging.getLogger(__name__)

# Utility functions
def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float.

    Args:
        value: The value to convert
        default: The default value to return if conversion fails

    Returns:
        The converted float value or the default
    """
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def safe_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    """Safely get an attribute from an object that may be a dictionary or object.

    Args:
        obj: The object to get the attribute from
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist

    Returns:
        The attribute value or the default
    """
    if obj is None:
        return default

    # Try attribute access first (for objects)
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name, default)

    # Try dictionary access (for dicts or dict-like objects)
    try:
        if isinstance(obj, dict) and attr_name in obj:
            return obj[attr_name]
        elif hasattr(obj, "get"):
            return obj.get(attr_name, default)
    except (TypeError, KeyError):
        pass

    return default

from common.utils import format_currency, calculate_risk_reward
from common.events import publish_event
from common.event_constants import EventType

# Type alias for SQLAlchemy models
Model = TypeVar('Model')

def create_model(model_class: Type[Model], **kwargs) -> Model:
    """Safely create a SQLAlchemy model instance with keyword arguments.

    This helper function works around type checking issues with SQLAlchemy models.

    Args:
        model_class: The SQLAlchemy model class to instantiate
        **kwargs: Keyword arguments to pass to the model constructor

    Returns:
        A new instance of the model
    """
    # Using type ignore because SQLAlchemy models have special keyword handling
    return model_class(**kwargs)  # type: ignore

def update_model_attr(model: Any, attr_name: str, value: Any) -> None:
    """Safely update a SQLAlchemy model attribute.

    This helper function works around type checking issues with SQLAlchemy models.

    Args:
        model: The SQLAlchemy model instance to update
        attr_name: The name of the attribute to update
        value: The new value for the attribute
    """
    setattr(model, attr_name, value)

# Configure logger
logger = logging.getLogger(__name__)

# Trading client (will be initialized)
trading_client = None

def initialize_position_manager():
    """Initialize the position manager with Alpaca client."""
    from alpaca.trading.client import TradingClient

    global trading_client

    api_key = os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        logger.warning("Alpaca API credentials not found. Position manager will run in limited mode.")
        return False

    try:
        # Initialize paper trading client
        trading_client = TradingClient(api_key, api_secret, paper=True)
        logger.info("Alpaca Trading client initialized for position manager")
        return True
    except Exception as e:
        logger.error(f"Error initializing Alpaca Trading client: {str(e)}")
        return False

def get_all_positions() -> List[Dict[str, Any]]:
    """Get all positions from Alpaca and local database."""
    positions = []

    # Get positions from database
    db_positions = PositionModel.query.filter_by(closed_at=None).all()
    for position in db_positions:
        positions.append({
            "id": position.id,
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avg_entry_price": position.avg_entry_price,
            "side": position.side,
            "market_value": position.market_value,
            "cost_basis": position.cost_basis,
            "unrealized_pl": position.unrealized_pl,
            "unrealized_plpc": position.unrealized_plpc,
            "current_price": position.current_price,
            "lastday_price": position.lastday_price,
            "change_today": position.change_today,
            "created_at": position.created_at.isoformat() if position.created_at else None
        })

    # Get positions from Alpaca if available
    if trading_client:
        try:
            alpaca_positions = trading_client.get_all_positions()
            # Sync positions from Alpaca to our database
            sync_positions_from_alpaca(alpaca_positions)

            # Add any positions from Alpaca that are not in our list
            for ap in alpaca_positions:
                # Extract required attributes safely with type checking
                try:
                    # Get symbol safely using safe_attr helper
                    symbol = safe_attr(ap, 'symbol')
                    if not symbol:
                        logger.warning(f"Position object missing symbol attribute: {ap}")
                        continue

                    # Convert to string
                    symbol = str(symbol)

                    if not any(p["symbol"] == symbol for p in positions):
                        # Extract and convert other attributes safely
                        try:
                            # Extract quantity using helper function
                            qty_value = safe_attr(ap, 'qty')
                            qty = int(qty_value) if qty_value is not None else 0

                            # Extract avg_entry_price using helper function
                            avg_entry_price = safe_float(safe_attr(ap, 'avg_entry_price'))

                            # Extract side using helper function
                            side_value = safe_attr(ap, 'side', 'long')  # Default to long
                            side = "long" if str(side_value).lower() == "long" else "short"

                            # Use the module-level safe_float function

                            # Build position dictionary with safe attribute access using helper functions
                            position_data = {
                                "symbol": symbol,
                                "quantity": qty,
                                "avg_entry_price": avg_entry_price,
                                "side": side,
                                "market_value": safe_float(safe_attr(ap, 'market_value')),
                                "cost_basis": safe_float(safe_attr(ap, 'cost_basis')),
                                "unrealized_pl": safe_float(safe_attr(ap, 'unrealized_pl')),
                                "unrealized_plpc": safe_float(safe_attr(ap, 'unrealized_plpc')),
                                "current_price": safe_float(safe_attr(ap, 'current_price')),
                                "lastday_price": safe_float(safe_attr(ap, 'lastday_price')),
                                "change_today": safe_float(safe_attr(ap, 'change_today')),
                                "created_at": None
                            }

                            positions.append(position_data)
                        except Exception as e:
                            logger.error(f"Error processing position {symbol}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error extracting data from Alpaca position: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching positions from Alpaca: {str(e)}")

    return positions

def sync_positions_from_alpaca(alpaca_positions: Union[List[Position], RawData, List[Any]]) -> None:
    """Sync positions from Alpaca to our local database.

    Args:
        alpaca_positions: List of position objects from Alpaca API or raw data.
            Each position object has attributes like symbol, qty, avg_entry_price, etc.
    """
    try:
        # Get current positions from our database
        db_positions = PositionModel.query.filter_by(closed_at=None).all()
        db_position_symbols = {p.symbol for p in db_positions}

        # Initialize list of alpaca symbols for tracking closed positions
        alpaca_symbols = set()

        # Process Alpaca positions
        for ap in alpaca_positions:
            # Type validation - ensure ap is a proper Alpaca position object
            if not hasattr(ap, 'symbol'):
                logger.warning(f"Skipping invalid position object: {ap}")
                continue

            # Get position symbol and add to our tracking set
            symbol = str(ap.symbol)
            alpaca_symbols.add(symbol)

            # Type-safe attribute access with defaults
            try:
                qty = int(ap.qty) if hasattr(ap, 'qty') else 0
                avg_entry_price = float(ap.avg_entry_price) if hasattr(ap, 'avg_entry_price') else 0.0
                side_value = str(ap.side) if hasattr(ap, 'side') else "long"
                side = "long" if side_value == "long" else "short"
                market_value = float(ap.market_value) if hasattr(ap, 'market_value') else 0.0
                cost_basis = float(ap.cost_basis) if hasattr(ap, 'cost_basis') else 0.0
                unrealized_pl = float(ap.unrealized_pl) if hasattr(ap, 'unrealized_pl') else 0.0
                unrealized_plpc = float(ap.unrealized_plpc) if hasattr(ap, 'unrealized_plpc') else 0.0
                current_price = float(ap.current_price) if hasattr(ap, 'current_price') else 0.0
                lastday_price = float(ap.lastday_price) if hasattr(ap, 'lastday_price') else 0.0
                change_today = float(ap.change_today) if hasattr(ap, 'change_today') else 0.0
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing position data for {symbol}: {str(e)}")
                continue

            # Check if we already have this position in our DB
            if symbol in db_position_symbols:
                # Update existing position
                position = next(p for p in db_positions if p.symbol == symbol)
                # Use setattr for SQLAlchemy models to avoid type checking issues
                setattr(position, 'quantity', qty)
                setattr(position, 'avg_entry_price', avg_entry_price)
                setattr(position, 'side', side)
                setattr(position, 'market_value', market_value)
                setattr(position, 'cost_basis', cost_basis)
                setattr(position, 'unrealized_pl', unrealized_pl)
                setattr(position, 'unrealized_plpc', unrealized_plpc)
                setattr(position, 'current_price', current_price)
                setattr(position, 'lastday_price', lastday_price)
                setattr(position, 'change_today', change_today)
                setattr(position, 'updated_at', datetime.utcnow())

                # Remove from set to track remaining positions
                db_position_symbols.remove(symbol)
            else:
                # Create new position entry using helper function
                new_position = create_model(PositionModel,
                    symbol=symbol,
                    quantity=qty,
                    avg_entry_price=avg_entry_price,
                    side=side,
                    market_value=market_value,
                    cost_basis=cost_basis,
                    unrealized_pl=unrealized_pl,
                    unrealized_plpc=unrealized_plpc,
                    current_price=current_price,
                    lastday_price=lastday_price,
                    change_today=change_today,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(new_position)

                # Create notification for new position with helper function
                notification = create_model(NotificationModel,
                    type="position",
                    title=f"New Position: {symbol}",
                    message=f"New position opened: {qty} {symbol} at {format_currency(avg_entry_price)}",
                    meta_data=json.dumps({
                        "symbol": symbol,
                        "quantity": qty,
                        "price": avg_entry_price,
                        "side": side
                    }),
                    read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)

        # Mark positions not in Alpaca as closed
        for symbol in db_position_symbols:
            position = next(p for p in db_positions if p.symbol == symbol)
            position.closed_at = datetime.utcnow()

            # Create notification for closed position using helper function
            notification = create_model(NotificationModel,
                type="position",
                title=f"Position Closed: {position.symbol}",
                message=f"Position closed: {position.quantity} {position.symbol} with P&L: {format_currency(position.unrealized_pl)} ({position.unrealized_plpc:.2f}%)",
                meta_data=json.dumps({
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "pnl": position.unrealized_pl,
                    "pnl_percent": position.unrealized_plpc
                }),
                read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)

        # Commit all changes
        db.session.commit()

    except Exception as e:
        logger.error(f"Error syncing positions from Alpaca: {str(e)}")
        db.session.rollback()

def get_position(symbol: str) -> Optional[Dict[str, Any]]:
    """Get a specific position by symbol."""
    # Try to get from database first
    position = PositionModel.query.filter_by(symbol=symbol, closed_at=None).first()
    if position:
        return {
            "id": position.id,
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avg_entry_price": position.avg_entry_price,
            "side": position.side,
            "market_value": position.market_value,
            "cost_basis": position.cost_basis,
            "unrealized_pl": position.unrealized_pl,
            "unrealized_plpc": position.unrealized_plpc,
            "current_price": position.current_price,
            "lastday_price": position.lastday_price,
            "change_today": position.change_today,
            "created_at": position.created_at.isoformat() if position.created_at else None
        }

    # If not in database, try getting from Alpaca
    if trading_client:
        try:
            alpaca_position = trading_client.get_open_position(symbol)
            if alpaca_position:
                # Add to database using helper function
                # Extract data safely using helper functions
                qty_value = safe_attr(alpaca_position, 'qty')
                qty = int(qty_value) if qty_value is not None else 0

                side_value = safe_attr(alpaca_position, 'side', 'long')
                side = "long" if str(side_value).lower() == "long" else "short"

                new_position = create_model(PositionModel,
                    symbol=symbol,
                    quantity=qty,
                    avg_entry_price=safe_float(safe_attr(alpaca_position, 'avg_entry_price')),
                    side=side,
                    market_value=safe_float(safe_attr(alpaca_position, 'market_value')),
                    cost_basis=safe_float(safe_attr(alpaca_position, 'cost_basis')),
                    unrealized_pl=safe_float(safe_attr(alpaca_position, 'unrealized_pl')),
                    unrealized_plpc=safe_float(safe_attr(alpaca_position, 'unrealized_plpc')),
                    current_price=safe_float(safe_attr(alpaca_position, 'current_price')),
                    lastday_price=safe_float(safe_attr(alpaca_position, 'lastday_price')),
                    change_today=safe_float(safe_attr(alpaca_position, 'change_today')),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(new_position)
                db.session.commit()

                # Return position data using the same helper functions
                return {
                    "id": new_position.id,
                    "symbol": symbol,
                    "quantity": qty,
                    "avg_entry_price": safe_float(safe_attr(alpaca_position, 'avg_entry_price')),
                    "side": side,
                    "market_value": safe_float(safe_attr(alpaca_position, 'market_value')),
                    "cost_basis": safe_float(safe_attr(alpaca_position, 'cost_basis')),
                    "unrealized_pl": safe_float(safe_attr(alpaca_position, 'unrealized_pl')),
                    "unrealized_plpc": safe_float(safe_attr(alpaca_position, 'unrealized_plpc')),
                    "current_price": safe_float(safe_attr(alpaca_position, 'current_price')),
                    "lastday_price": safe_float(safe_attr(alpaca_position, 'lastday_price')),
                    "change_today": safe_float(safe_attr(alpaca_position, 'change_today')),
                    "created_at": new_position.created_at.isoformat()
                }
        except Exception as e:
            logger.error(f"Error fetching position from Alpaca: {str(e)}")

    return None

def close_position(symbol: str) -> Dict[str, Any]:
    """Close a position by symbol using Alpaca's close_position method."""
    if not trading_client:
        return {
            "success": False,
            "message": "Trading client not initialized"
        }

    try:
        # Close the position through Alpaca's direct method
        trading_client.close_position(symbol)

        # Mark as closed in our database
        position = PositionModel.query.filter_by(symbol=symbol, closed_at=None).first()
        if position:
            position.closed_at = datetime.utcnow()
            db.session.commit()

            # Create notification using helper function
            notification = create_model(NotificationModel,
                type="position",
                title=f"Position Closed: {symbol}",
                message=f"Position closed: {position.quantity} {symbol} with P&L: {format_currency(position.unrealized_pl)} ({position.unrealized_plpc:.2f}%)",
                meta_data=json.dumps({
                    "symbol": symbol,
                    "quantity": position.quantity,
                    "pnl": position.unrealized_pl,
                    "pnl_percent": position.unrealized_plpc
                }),
                read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
            db.session.commit()

        return {
            "success": True,
            "message": f"Position {symbol} closed successfully"
        }
    except Exception as e:
        logger.error(f"Error closing position {symbol}: {str(e)}")
        return {
            "success": False,
            "message": f"Error closing position: {str(e)}"
        }

def close_position_partial(symbol: str, quantity: int) -> Dict[str, Any]:
    """Close a partial position by symbol and quantity."""
    if not trading_client:
        return {
            "success": False,
            "message": "Trading client not initialized"
        }

    try:
        # Get current position
        position = get_position(symbol)
        if not position:
            return {
                "success": False,
                "message": f"No open position found for {symbol}"
            }

        current_qty = position["quantity"]
        if quantity > current_qty:
            return {
                "success": False,
                "message": f"Cannot close {quantity} shares/contracts, only {current_qty} available"
            }

        # Close partial position
        order = trading_client.submit_order(
            symbol=symbol,
            qty=quantity,
            side="sell" if position["side"] == "long" else "buy",
            type="market",
            time_in_force="day"
        )

        # If full position is closed, mark as closed
        if quantity == current_qty:
            db_position = PositionModel.query.filter_by(symbol=symbol, closed_at=None).first()
            if db_position:
                db_position.closed_at = datetime.utcnow()
                db.session.commit()

        # Create notification using helper function
        notification = create_model(NotificationModel,
            type="position",
            title=f"Partial Position Closed: {symbol}",
            message=f"Closed {quantity} of {current_qty} {symbol}",
            meta_data=json.dumps({
                "symbol": symbol,
                "quantity": quantity,
                "total_quantity": current_qty,
                "order_id": order.id
            }),
            read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        db.session.commit()

        return {
            "success": True,
            "message": f"Closed {quantity} of {current_qty} {symbol}",
            "order_id": order.id
        }
    except Exception as e:
        logger.error(f"Error closing partial position {symbol}: {str(e)}")
        return {
            "success": False,
            "message": f"Error closing partial position: {str(e)}"
        }

def scale_position(symbol: str, additional_quantity: int) -> Dict[str, Any]:
    """Add to an existing position."""
    if not trading_client:
        return {
            "success": False,
            "message": "Trading client not initialized"
        }

    try:
        # Get current position
        position = get_position(symbol)
        if not position:
            return {
                "success": False,
                "message": f"No open position found for {symbol}"
            }

        # Scale position
        order = trading_client.submit_order(
            symbol=symbol,
            qty=additional_quantity,
            side="buy" if position["side"] == "long" else "sell",
            type="market",
            time_in_force="day"
        )

        # Create notification using helper function
        notification = create_model(NotificationModel,
            type="position",
            title=f"Position Scaled: {symbol}",
            message=f"Added {additional_quantity} to position in {symbol}",
            meta_data=json.dumps({
                "symbol": symbol,
                "quantity": additional_quantity,
                "previous_quantity": position["quantity"],
                "order_id": order.id
            }),
            read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        db.session.commit()

        return {
            "success": True,
            "message": f"Added {additional_quantity} to position in {symbol}",
            "order_id": order.id
        }
    except Exception as e:
        logger.error(f"Error scaling position {symbol}: {str(e)}")
        return {
            "success": False,
            "message": f"Error scaling position: {str(e)}"
        }

def calculate_portfolio_metrics() -> Dict[str, Any]:
    """Calculate portfolio-wide metrics."""
    metrics = {
        "total_positions": 0,
        "total_market_value": 0.0,
        "total_cost_basis": 0.0,
        "total_unrealized_pl": 0.0,
        "total_unrealized_plpc": 0.0,
        "long_exposure": 0.0,
        "short_exposure": 0.0,
        "net_exposure": 0.0,
        "gross_exposure": 0.0,
        "positions_by_side": {"long": 0, "short": 0},
        "positions_by_profitability": {"profit": 0, "loss": 0}
    }

    positions = get_all_positions()
    if not positions:
        return metrics

    metrics["total_positions"] = len(positions)

    for position in positions:
        metrics["total_market_value"] += position.get("market_value", 0)
        metrics["total_cost_basis"] += position.get("cost_basis", 0)
        metrics["total_unrealized_pl"] += position.get("unrealized_pl", 0)

        # Track by side
        side = position.get("side", "long")
        metrics["positions_by_side"][side] += 1

        if side == "long":
            metrics["long_exposure"] += position.get("market_value", 0)
        else:
            metrics["short_exposure"] += position.get("market_value", 0)

        # Track by profitability
        if position.get("unrealized_pl", 0) > 0:
            metrics["positions_by_profitability"]["profit"] += 1
        else:
            metrics["positions_by_profitability"]["loss"] += 1

    # Calculate net and gross exposure
    metrics["net_exposure"] = metrics["long_exposure"] - metrics["short_exposure"]
    metrics["gross_exposure"] = metrics["long_exposure"] + metrics["short_exposure"]

    # Calculate overall P&L percentage
    if metrics["total_cost_basis"] > 0:
        metrics["total_unrealized_plpc"] = (metrics["total_unrealized_pl"] / metrics["total_cost_basis"]) * 100

    return metrics

def calculate_position_size(
    symbol: str, 
    price: float, 
    risk_percent: float = 1.0,
    stop_loss_percent: float = 5.0
) -> int:
    """Calculate position size based on risk parameters."""
    if not trading_client:
        return 1  # Default to 1 contract if no trading client

    try:
        # Get account equity
        account = trading_client.get_account()
        equity = float(account.equity)

        # Calculate max risk amount (e.g., 1% of equity)
        max_risk_amount = equity * (risk_percent / 100)

        # Calculate stop loss price
        stop_loss_price = price * (1 - (stop_loss_percent / 100))

        # Calculate risk per contract
        risk_per_contract = price - stop_loss_price

        # Calculate position size
        if risk_per_contract > 0:
            position_size = math.floor(max_risk_amount / risk_per_contract)
        else:
            position_size = 1

        # Ensure at least 1 contract
        position_size = max(1, position_size)

        logger.info(f"Calculated position size for {symbol}: {position_size} contracts")
        return position_size
    except Exception as e:
        logger.error(f"Error calculating position size: {str(e)}")
        return 1  # Default to 1 contract on error

def get_position_history(days: int = 30) -> List[Dict[str, Any]]:
    """Get history of closed positions."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    closed_positions = (
        PositionModel.query
        .filter(PositionModel.closed_at.isnot(None))
        .filter(PositionModel.closed_at >= cutoff_date)
        .order_by(PositionModel.closed_at.desc())
        .all()
    )

    results = []
    for position in closed_positions:
        results.append({
            "id": position.id,
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avg_entry_price": position.avg_entry_price,
            "side": position.side,
            "unrealized_pl": position.unrealized_pl,
            "unrealized_plpc": position.unrealized_plpc,
            "created_at": position.created_at.isoformat() if position.created_at else None,
            "closed_at": position.closed_at.isoformat() if position.closed_at else None,
            "duration": (position.closed_at - position.created_at).total_seconds() // 60 if position.closed_at and position.created_at else None
        })

    return results

def start_position_update_thread():
    """Start a background thread to update positions periodically."""
    # Import Flask app here to avoid circular imports
    from app import app

    def update_positions_job():
        """Run position updates with Flask application context."""
        while True:
            try:
                # Use Flask application context for database operations
                with app.app_context():
                    # Sync positions from Alpaca
                    if trading_client:
                        alpaca_positions = trading_client.get_all_positions()
                        sync_positions_from_alpaca(alpaca_positions)
                        logger.debug(f"Updated {len(alpaca_positions)} positions from Alpaca")
            except Exception as e:
                logger.error(f"Error in position update thread: {str(e)}")

            # Sleep for 60 seconds
            time.sleep(60)

    # Start thread
    update_thread = threading.Thread(target=update_positions_job, daemon=True)
    update_thread.start()
    logger.info("Position update thread started")

    return update_thread

# Initialize position manager
initialize_position_manager()

# Routes for position manager API
def register_position_routes(app):
    from flask import Blueprint, jsonify, request

    position_routes = Blueprint('position_routes', __name__)

    @position_routes.route('/api/positions', methods=['GET'])
    def get_positions_api():
        """Get all positions."""
        positions = get_all_positions()
        return jsonify(positions)

    @position_routes.route('/api/positions/<symbol>', methods=['GET'])
    def get_position_api(symbol):
        """Get a specific position by symbol."""
        position = get_position(symbol)

        if not position:
            return jsonify({
                "error": f"Position for {symbol} not found"
            }), 404

        return jsonify(position)

    @position_routes.route('/api/positions/<symbol>/close', methods=['POST'])
    def close_position_api(symbol):
        """Close a position by symbol."""
        quantity = request.json.get('quantity')

        if quantity:
            try:
                quantity = int(quantity)  # Ensure quantity is an integer
                result = close_position_partial(symbol, quantity)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "message": "Quantity must be a valid integer"
                }), 400
        else:
            result = close_position(symbol)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @position_routes.route('/api/positions/<symbol>/scale', methods=['POST'])
    def scale_position_api(symbol):
        """Add to an existing position."""
        quantity = request.json.get('quantity')

        if not quantity:
            return jsonify({
                "success": False,
                "message": "Quantity is required"
            }), 400

        try:
            quantity = int(quantity)  # Ensure quantity is an integer
            result = scale_position(symbol, quantity)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Quantity must be a valid integer"
            }), 400

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @position_routes.route('/api/positions/metrics', methods=['GET'])
    def portfolio_metrics_api():
        """Get portfolio-wide metrics."""
        metrics = calculate_portfolio_metrics()
        return jsonify(metrics)

    @position_routes.route('/api/positions/history', methods=['GET'])
    def position_history_api():
        """Get history of closed positions."""
        days = request.args.get('days', 30, type=int)
        history = get_position_history(days)
        return jsonify(history)

    # Register blueprint
    app.register_blueprint(position_routes)

    return position_routes

# Start position update thread when app is ready
def start_position_manager():
    """Start the position manager when app is ready."""
    start_position_update_thread()

# This will be called from main.py after all routes are registered