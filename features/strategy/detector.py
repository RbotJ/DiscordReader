"""
Strategy detector for price triggers.

This module monitors market data and detects when price levels
defined in trading setups are triggered, generating signals for execution.
"""
import os
import logging
import threading
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text

from app import app, db
from common.db_models import (
    SignalModel, TickerSetupModel, PriceTriggerModel, SetupModel,
    NotificationModel
)
from features.market.client import (
    register_price_callback, initialize_clients, add_symbols_to_watchlist
)
from common.events.constants import EventChannels
from common.db import publish_event, get_latest_events

# Configure logger
logger = logging.getLogger(__name__)

# Global variables
detector_running = False
detector_thread = None
active_triggers = {}  # symbol -> list of triggers
symbols_processed = set()
detector_symbols = set()

# Create blueprint for API routes
from flask import Blueprint, request, jsonify
strategy_routes = Blueprint('strategy', __name__)


def start_detector():
    """Start the strategy detector."""
    global detector_running, detector_thread

    # If already running, do nothing
    if detector_running:
        return

    # Set the running flag
    detector_running = True

    # Initialize clients
    initialize_clients()

    # Load active triggers from database
    load_active_triggers()

    # Register the price callback
    register_price_callback(process_price_update)

    # Start the watchdog thread
    detector_thread = threading.Thread(target=detector_watchdog)
    detector_thread.daemon = True
    detector_thread.start()

    logger.info("Strategy detector started")


def stop_detector():
    """Stop the strategy detector."""
    global detector_running, detector_thread

    # If not running, do nothing
    if not detector_running:
        return

    # Set the running flag
    detector_running = False

    # Wait for the thread to stop
    if detector_thread:
        detector_thread.join(timeout=5)

    detector_thread = None

    logger.info("Strategy detector stopped")


def detector_status():
    """Get the status of the strategy detector."""
    global detector_running, active_triggers, symbols_processed, detector_symbols

    return {
        "running": detector_running,
        "active_triggers_count": sum(len(triggers) for triggers in active_triggers.values()),
        "active_symbols_count": len(detector_symbols),
        "processed_symbols_count": len(symbols_processed),
        "active_symbols": list(detector_symbols)
    }


def load_active_triggers():
    """Load active triggers from the database."""
    global active_triggers, detector_symbols

    try:
        # Clear existing triggers
        active_triggers = {}
        detector_symbols = set()

        with app.app_context():
            # Query active price triggers with their signals and ticker details
            triggers = db.session.execute(text("""
                SELECT 
                    pt.id, pt.symbol, pt.comparison, pt.trigger_value, 
                    s.id as signal_id, s.category, s.aggressiveness, s.targets,
                    ts.id as ticker_setup_id, ts.symbol as ticker_symbol, 
                    setup.date as setup_date
                FROM 
                    price_triggers pt
                JOIN 
                    signals s ON pt.signal_id = s.id
                JOIN 
                    ticker_setups ts ON s.ticker_setup_id = ts.id
                JOIN 
                    setups setup ON ts.setup_id = setup.id
                WHERE 
                    pt.active = TRUE
                ORDER BY 
                    setup.date DESC
            """)).fetchall()

            # Process triggers
            for trigger in triggers:
                symbol = trigger.symbol

                # Add to active triggers
                if symbol not in active_triggers:
                    active_triggers[symbol] = []

                # Add trigger details
                trigger_details = {
                    "id": trigger.id,
                    "symbol": symbol,
                    "comparison": trigger.comparison,
                    "trigger_value": trigger.trigger_value,
                    "signal_id": trigger.signal_id,
                    "category": trigger.category,
                    "aggressiveness": trigger.aggressiveness,
                    "targets": trigger.targets,
                    "ticker_setup_id": trigger.ticker_setup_id,
                    "ticker_symbol": trigger.ticker_symbol,
                    "setup_date": trigger.setup_date.isoformat() if trigger.setup_date else None
                }

                active_triggers[symbol].append(trigger_details)
                detector_symbols.add(symbol)

            # Add symbols to watchlist
            if detector_symbols:
                add_symbols_to_watchlist(list(detector_symbols))

            logger.info(f"Loaded {sum(len(triggers) for triggers in active_triggers.values())} "
                        f"active triggers for {len(detector_symbols)} symbols")

    except Exception as e:
        logger.error(f"Error loading active triggers: {e}")


def process_price_update(symbol: str, price: float):
    """Process a price update for a symbol."""
    global active_triggers, symbols_processed

    # Add to processed symbols
    symbols_processed.add(symbol)

    # Check if we have triggers for this symbol
    if symbol not in active_triggers:
        return

    # Check each trigger
    triggers_to_remove = []

    for idx, trigger in enumerate(active_triggers[symbol]):
        triggered = check_trigger(trigger, price)

        if triggered:
            # Mark the trigger as triggered in the database
            mark_trigger_triggered(trigger["id"])

            # Create notification
            create_signal_notification(trigger, price)

            # Add to removal list
            triggers_to_remove.append(idx)

    # Remove triggered triggers
    for idx in sorted(triggers_to_remove, reverse=True):
        active_triggers[symbol].pop(idx)

    # If no more triggers for this symbol, remove it
    if len(active_triggers[symbol]) == 0:
        del active_triggers[symbol]
        # Note: We don't remove from watchlist since other components might need it


def check_trigger(trigger: Dict[str, Any], price: float) -> bool:
    """Check if a trigger is triggered by the current price."""
    comparison = trigger["comparison"]
    trigger_value = trigger["trigger_value"]

    # Convert trigger_value to list if it's not
    if isinstance(trigger_value, (int, float)):
        trigger_value = [float(trigger_value)]
    elif isinstance(trigger_value, str):
        try:
            trigger_value = [float(trigger_value)]
        except ValueError:
            # Handle case where it might be a JSON string: ["123.45", "234.56"]
            if trigger_value.startswith('[') and trigger_value.endswith(']'):
                try:
                    import json
                    trigger_value = [float(v) for v in json.loads(trigger_value)]
                except:
                    logger.error(f"Failed to parse trigger value: {trigger_value}")
                    return False

    # Check comparison
    if comparison == "above" and price >= trigger_value[0]:
        return True
    elif comparison == "below" and price <= trigger_value[0]:
        return True
    elif comparison == "near" and abs(price - trigger_value[0]) <= (trigger_value[0] * 0.005):  # Within 0.5%
        return True
    elif comparison == "range" and len(trigger_value) >= 2:
        return trigger_value[0] <= price <= trigger_value[1]

    return False


def mark_trigger_triggered(trigger_id: int):
    """Mark a trigger as triggered in the database."""
    try:
        with app.app_context():
            # Update the trigger
            db.session.execute(text("""
                UPDATE price_triggers
                SET 
                    active = FALSE,
                    triggered_at = NOW()
                WHERE
                    id = :trigger_id
            """), {"trigger_id": trigger_id})

            db.session.commit()

            logger.info(f"Marked trigger {trigger_id} as triggered")

    except Exception as e:
        logger.error(f"Error marking trigger {trigger_id} as triggered: {e}")


def create_signal_notification(trigger: Dict[str, Any], price: float):
    """Create a notification for a triggered signal."""
    try:
        symbol = trigger["symbol"]
        category = trigger["category"]

        # Determine direction based on category
        direction = "bullish" if category in ["breakout", "bounce"] else "bearish"

        # Create notification message
        title = f"{symbol} {category.capitalize()} Signal Triggered"
        message = (f"{symbol} price of ${price:.2f} has triggered a {category} signal "
                   f"with {trigger['aggressiveness']} aggressiveness.")

        # Add target information
        targets = trigger["targets"]
        if targets and len(targets) > 0:
            targets_str = ", ".join([f"${t:.2f}" for t in targets])
            message += f" Price targets: {targets_str}"

        # Meta data for the notification
        meta_data = {
            "symbol": symbol,
            "price": price,
            "category": category,
            "direction": direction,
            "signal_id": trigger["signal_id"],
            "ticker_setup_id": trigger["ticker_setup_id"],
            "targets": targets
        }

        with app.app_context():
            # Create notification
            notification = NotificationModel()
            notification.type = "signal"
            notification.title = title
            notification.message = message
            notification.meta_data = meta_data
            notification.read = False

            db.session.add(notification)
            db.session.commit()

            logger.info(f"Created notification for triggered signal: {title}")

    except Exception as e:
        logger.error(f"Error creating notification for triggered signal: {e}")


def create_price_trigger(
    symbol: str,
    comparison: str,
    trigger_value: Any,
    signal_id: int
) -> Optional[int]:
    """Create a new price trigger."""
    try:
        with app.app_context():
            # Create the trigger
            trigger = PriceTriggerModel()
            trigger.symbol = symbol
            trigger.comparison = comparison
            trigger.trigger_value = trigger_value
            trigger.signal_id = signal_id
            trigger.active = True

            db.session.add(trigger)
            db.session.commit()

            # Add to active triggers
            load_active_triggers()

            logger.info(f"Created price trigger for {symbol} {comparison} {trigger_value}")

            return trigger.id

    except Exception as e:
        logger.error(f"Error creating price trigger: {e}")
        return None


def deactivate_price_trigger(trigger_id: int) -> bool:
    """Deactivate a price trigger."""
    try:
        with app.app_context():
            # Update the trigger
            trigger = db.session.query(PriceTriggerModel).filter_by(id=trigger_id).first()

            if not trigger:
                logger.warning(f"Trigger {trigger_id} not found")
                return False

            trigger.active = False
            db.session.commit()

            # Reload active triggers
            load_active_triggers()

            logger.info(f"Deactivated price trigger {trigger_id}")

            return True

    except Exception as e:
        logger.error(f"Error deactivating price trigger {trigger_id}: {e}")
        return False


def get_active_price_triggers() -> List[Dict[str, Any]]:
    """Get all active price triggers."""
    try:
        with app.app_context():
            # Query active price triggers
            triggers = db.session.execute(text("""
                SELECT 
                    pt.id, pt.symbol, pt.comparison, pt.trigger_value, 
                    s.id as signal_id, s.category, s.aggressiveness, s.targets,
                    ts.id as ticker_setup_id, ts.symbol as ticker_symbol, 
                    setup.date as setup_date
                FROM 
                    price_triggers pt
                JOIN 
                    signals s ON pt.signal_id = s.id
                JOIN 
                    ticker_setups ts ON s.ticker_setup_id = ts.id
                JOIN 
                    setups setup ON ts.setup_id = setup.id
                WHERE 
                    pt.active = TRUE
                ORDER BY 
                    setup.date DESC
            """)).fetchall()

            # Format results
            result = []
            for trigger in triggers:
                trigger_dict = {
                    "id": trigger.id,
                    "symbol": trigger.symbol,
                    "comparison": trigger.comparison,
                    "trigger_value": trigger.trigger_value,
                    "signal_id": trigger.signal_id,
                    "category": trigger.category,
                    "aggressiveness": trigger.aggressiveness,
                    "targets": trigger.targets,
                    "ticker_setup_id": trigger.ticker_setup_id,
                    "ticker_symbol": trigger.ticker_symbol,
                    "setup_date": trigger.setup_date.isoformat() if trigger.setup_date else None
                }
                result.append(trigger_dict)

            return result

    except Exception as e:
        logger.error(f"Error getting active price triggers: {e}")
        return []


def detector_watchdog():
    """Background thread to periodically check and reload triggers."""
    global detector_running

    logger.info("Starting detector watchdog thread")

    while detector_running:
        # Sleep for 5 minutes
        for _ in range(30):  # 30 x 10 seconds = 5 minutes
            if not detector_running:
                break
            threading.Event().wait(10)

        if not detector_running:
            break

        try:
            # Reload triggers to catch any new ones
            logger.info("Reloading active triggers")
            load_active_triggers()
        except Exception as e:
            logger.error(f"Error in detector watchdog: {e}")

    logger.info("Detector watchdog thread stopped")


def generate_triggers_from_signals():
    """Generate price triggers from existing signals."""
    try:
        with app.app_context():
            # Query signals without triggers
            signals = db.session.execute(text("""
                SELECT 
                    s.id, s.category, s.comparison, s.trigger_value, 
                    ts.symbol
                FROM 
                    signals s
                JOIN 
                    ticker_setups ts ON s.ticker_setup_id = ts.id
                LEFT JOIN 
                    price_triggers pt ON pt.signal_id = s.id
                WHERE 
                    pt.id IS NULL
                    AND s.active = TRUE
            """)).fetchall()

            triggers_created = 0

            # Create triggers for each signal
            for signal in signals:
                try:
                    # Create trigger
                    trigger = PriceTriggerModel()
                    trigger.symbol = signal.symbol
                    trigger.comparison = signal.comparison
                    trigger.trigger_value = signal.trigger_value
                    trigger.signal_id = signal.id
                    trigger.active = True

                    db.session.add(trigger)
                    triggers_created += 1

                except Exception as e:
                    logger.error(f"Error creating trigger for signal {signal.id}: {e}")

            # Commit all changes
            db.session.commit()

            # Reload active triggers
            load_active_triggers()

            logger.info(f"Generated {triggers_created} price triggers from signals")

            return triggers_created

    except Exception as e:
        logger.error(f"Error generating triggers from signals: {e}")
        return 0


# API endpoints
@strategy_routes.route('/api/strategy/status', methods=['GET'])
def get_detector_status():
    """Get the status of the strategy detector."""
    status = detector_status()
    return jsonify(status)


@strategy_routes.route('/api/strategy/control', methods=['POST'])
def control_detector():
    """Start or stop the strategy detector."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    action = data.get('action', '').lower()

    if action == 'start':
        start_detector()
        return jsonify({
            "success": True,
            "status": "started"
        })
    elif action == 'stop':
        stop_detector()
        return jsonify({
            "success": True,
            "status": "stopped"
        })
    else:
        return jsonify({
            "error": "Invalid action, must be 'start' or 'stop'"
        }), 400


@strategy_routes.route('/api/strategy/triggers', methods=['GET'])
def get_triggers():
    """Get all active price triggers."""
    triggers = get_active_price_triggers()
    return jsonify(triggers)


@strategy_routes.route('/api/strategy/triggers', methods=['POST'])
def create_trigger():
    """Create a new price trigger."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Validate input
    if not all(key in data for key in ['symbol', 'comparison', 'trigger_value', 'signal_id']):
        return jsonify({"error": "Missing required fields"}), 400

    # Create trigger
    trigger_id = create_price_trigger(
        data['symbol'],
        data['comparison'],
        data['trigger_value'],
        data['signal_id']
    )

    if trigger_id:
        return jsonify({
            "success": True,
            "trigger_id": trigger_id
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to create trigger"
        }), 500


@strategy_routes.route('/api/strategy/triggers/<int:trigger_id>', methods=['DELETE'])
def delete_trigger(trigger_id):
    """Deactivate a price trigger."""
    success = deactivate_price_trigger(trigger_id)

    if success:
        return jsonify({
            "success": True,
            "message": f"Trigger {trigger_id} deactivated"
        })
    else:
        return jsonify({
            "success": False,
            "error": f"Failed to deactivate trigger {trigger_id}"
        }), 500


@strategy_routes.route('/api/strategy/generate', methods=['POST'])
def generate_triggers():
    """Generate price triggers from existing signals."""
    count = generate_triggers_from_signals()

    return jsonify({
        "success": True,
        "triggers_created": count
    })