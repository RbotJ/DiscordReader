"""
Exit Rules Engine Module

This module handles the application of exit rules to open positions,
including profit targets, stop losses, and bias flips.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import time
import threading

from app import app, db
from common.db_models import (
    PositionModel, OrderModel, SignalModel, NotificationModel,
    OptionsContractModel, MarketDataModel, TickerSetupModel, BiasModel
)
from common.redis_utils import RedisClient
from features.management.position_manager import get_position, close_position, close_position_partial

# Configure logger
logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = RedisClient()

class ExitRule:
    """Base class for exit rules."""
    def should_exit(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited based on this rule."""
        raise NotImplementedError("Subclasses must implement should_exit")

class ProfitTargetRule(ExitRule):
    """Exit rule for profit targets."""
    def __init__(self, target_percent: float = 20.0):
        self.target_percent = target_percent
    
    def should_exit(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position has reached profit target."""
        if position.get("unrealized_plpc", 0) >= self.target_percent:
            return True, f"Profit target reached: {position['unrealized_plpc']:.2f}% >= {self.target_percent:.2f}%"
        return False, ""

class StopLossRule(ExitRule):
    """Exit rule for stop losses."""
    def __init__(self, stop_percent: float = -10.0):
        self.stop_percent = stop_percent
    
    def should_exit(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position has hit stop loss."""
        if position.get("unrealized_plpc", 0) <= self.stop_percent:
            return True, f"Stop loss triggered: {position['unrealized_plpc']:.2f}% <= {self.stop_percent:.2f}%"
        return False, ""

class SignalTargetRule(ExitRule):
    """Exit rule for predefined signal targets."""
    def should_exit(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position has reached a predefined signal target."""
        symbol = position.get("symbol", "")
        current_price = market_data.get("price", 0)
        
        # Get the latest signal for this symbol
        signal = (
            SignalModel.query
            .join(TickerSetupModel, SignalModel.ticker_setup_id == TickerSetupModel.id)
            .filter(TickerSetupModel.symbol == symbol.split()[0])  # Extract underlying from option symbol
            .order_by(SignalModel.created_at.desc())
            .first()
        )
        
        if not signal or not signal.targets:
            return False, ""
        
        targets = json.loads(signal.targets) if isinstance(signal.targets, str) else signal.targets
        
        # Check if we've hit a target
        if position.get("side") == "long":
            for target in targets:
                if current_price >= float(target):
                    return True, f"Reached price target: {current_price:.2f} >= {target:.2f}"
        else:  # short position
            for target in targets:
                if current_price <= float(target):
                    return True, f"Reached price target: {current_price:.2f} <= {target:.2f}"
        
        return False, ""

class BiasFlipRule(ExitRule):
    """Exit rule for bias flips."""
    def should_exit(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if market bias has flipped against position."""
        symbol = position.get("symbol", "")
        current_price = market_data.get("price", 0)
        position_side = position.get("side")
        
        # Extract underlying from option symbol (e.g., "SPY" from "SPY 05/17 400C")
        underlying = symbol.split()[0] if " " in symbol else symbol
        
        # Get the latest bias for this symbol
        bias = (
            BiasModel.query
            .join(TickerSetupModel, BiasModel.ticker_setup_id == TickerSetupModel.id)
            .filter(TickerSetupModel.symbol == underlying)
            .order_by(BiasModel.created_at.desc())
            .first()
        )
        
        if not bias:
            return False, ""
        
        # Check for bias flip
        if bias.flip_price_level is not None and bias.flip_direction:
            # Long position with bearish flip
            if position_side == "long" and bias.flip_direction == "bearish" and current_price <= bias.flip_price_level:
                return True, f"Bias flipped bearish below {bias.flip_price_level:.2f}"
            
            # Short position with bullish flip
            if position_side == "short" and bias.flip_direction == "bullish" and current_price >= bias.flip_price_level:
                return True, f"Bias flipped bullish above {bias.flip_price_level:.2f}"
        
        return False, ""

class TimeBasedRule(ExitRule):
    """Exit rule based on time in position."""
    def __init__(self, max_days: int = 3):
        self.max_days = max_days
    
    def should_exit(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position has been held for too long."""
        created_at = position.get("created_at")
        if not created_at:
            return False, ""
        
        # Parse ISO format if string
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        # Calculate days in position
        days_held = (datetime.utcnow() - created_at).days
        
        if days_held >= self.max_days:
            return True, f"Position held for {days_held} days (max: {self.max_days})"
        
        return False, ""

class ExitRulesEngine:
    """Engine to evaluate exit rules and execute position exits."""
    def __init__(self):
        """Initialize the exit rules engine with default rules."""
        self.rules = [
            ProfitTargetRule(target_percent=20.0),
            StopLossRule(stop_percent=-10.0),
            SignalTargetRule(),
            BiasFlipRule(),
            TimeBasedRule(max_days=5)
        ]
        self.running = False
        self.thread = None
    
    def add_rule(self, rule: ExitRule):
        """Add a new exit rule to the engine."""
        self.rules.append(rule)
    
    def evaluate_position(self, position: Dict[str, Any]) -> List[Tuple[bool, str]]:
        """Evaluate a position against all exit rules."""
        if not position:
            return []
        
        symbol = position.get("symbol", "")
        
        # Get latest market data for the symbol
        underlying = symbol.split()[0] if " " in symbol else symbol
        market_data = MarketDataModel.query.filter_by(symbol=underlying).order_by(MarketDataModel.timestamp.desc()).first()
        
        if not market_data:
            return []
        
        market_data_dict = {
            "symbol": market_data.symbol,
            "price": market_data.price,
            "timestamp": market_data.timestamp
        }
        
        # Evaluate each rule
        results = []
        for rule in self.rules:
            should_exit, reason = rule.should_exit(position, market_data_dict)
            if should_exit:
                results.append((True, reason))
        
        return results
    
    def process_exits(self):
        """Process exits for all open positions."""
        from features.management.position_manager import get_all_positions
        
        positions = get_all_positions()
        
        for position in positions:
            exit_results = self.evaluate_position(position)
            
            # If any exit rule triggers, close the position
            if any(should_exit for should_exit, _ in exit_results):
                reasons = [reason for _, reason in exit_results if reason]
                combined_reason = ", ".join(reasons)
                
                logger.info(f"Exiting position {position['symbol']} due to: {combined_reason}")
                
                # Close the position
                result = close_position(position["symbol"])
                
                if result["success"]:
                    # Log exit in database and notify
                    notification = NotificationModel()
                    notification.type = "exit"
                    notification.title = f"Automatic Exit: {position['symbol']}"
                    notification.message = f"Position automatically closed: {position['symbol']} due to: {combined_reason}"
                    notification.meta_data = json.dumps({
                        "symbol": position["symbol"],
                        "reason": combined_reason,
                        "unrealized_pl": position.get("unrealized_pl", 0),
                        "unrealized_plpc": position.get("unrealized_plpc", 0)
                    })
                    notification.read = False
                    notification.created_at = datetime.utcnow()
                    db.session.add(notification)
                    db.session.commit()
                    
                    # Publish to Redis for real-time updates
                    redis_client.publish("position_exits", json.dumps({
                        "symbol": position["symbol"],
                        "reason": combined_reason,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                else:
                    logger.error(f"Failed to exit position {position['symbol']}: {result['message']}")
    
    def run_exit_rules_job(self):
        """Run the exit rules job continuously."""
        # Import Flask app here to avoid circular imports
        from app import app
        
        while self.running:
            try:
                # Use Flask application context for database operations
                with app.app_context():
                    self.process_exits()
            except Exception as e:
                logger.error(f"Error in exit rules job: {str(e)}")
            
            # Sleep for 60 seconds
            time.sleep(60)
    
    def start(self):
        """Start the exit rules engine."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_exit_rules_job, daemon=True)
        self.thread.start()
        logger.info("Exit rules engine started")
    
    def stop(self):
        """Stop the exit rules engine."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            logger.info("Exit rules engine stopped")

# Global exit rules engine instance
exit_rules_engine = ExitRulesEngine()

def start_exit_rules_engine():
    """Start the exit rules engine."""
    exit_rules_engine.start()
    return exit_rules_engine

def stop_exit_rules_engine():
    """Stop the exit rules engine."""
    exit_rules_engine.stop()

def get_exit_rules_status():
    """Get the status of the exit rules engine."""
    return {
        "running": exit_rules_engine.running,
        "rule_count": len(exit_rules_engine.rules),
        "rules": [rule.__class__.__name__ for rule in exit_rules_engine.rules]
    }

# Routes for exit rules API
def register_exit_rules_routes(app):
    from flask import Blueprint, jsonify, request
    
    exit_rules_routes = Blueprint('exit_rules_routes', __name__)
    
    @exit_rules_routes.route('/api/exit-rules/status', methods=['GET'])
    def exit_rules_status_api():
        """Get status of the exit rules engine."""
        status = get_exit_rules_status()
        return jsonify(status)
    
    @exit_rules_routes.route('/api/exit-rules/start', methods=['POST'])
    def start_exit_rules_api():
        """Start the exit rules engine."""
        start_exit_rules_engine()
        return jsonify({
            "success": True,
            "message": "Exit rules engine started"
        })
    
    @exit_rules_routes.route('/api/exit-rules/stop', methods=['POST'])
    def stop_exit_rules_api():
        """Stop the exit rules engine."""
        stop_exit_rules_engine()
        return jsonify({
            "success": True,
            "message": "Exit rules engine stopped"
        })
    
    @exit_rules_routes.route('/api/exit-rules/evaluate/<symbol>', methods=['GET'])
    def evaluate_position_api(symbol):
        """Evaluate a specific position against exit rules."""
        from features.management.position_manager import get_position
        
        position = get_position(symbol)
        if not position:
            return jsonify({
                "error": f"Position for {symbol} not found"
            }), 404
        
        exit_results = exit_rules_engine.evaluate_position(position)
        
        return jsonify({
            "symbol": symbol,
            "should_exit": any(should_exit for should_exit, _ in exit_results),
            "reasons": [reason for _, reason in exit_results if reason]
        })
    
    # Register blueprint
    app.register_blueprint(exit_rules_routes)
    
    return exit_rules_routes

# Start exit rules engine when app is ready
def init_exit_rules_engine():
    """Initialize exit rules engine when app is ready."""
    # Wait a bit to ensure other services are up
    threading.Timer(5.0, start_exit_rules_engine).start()

# This will be called from main.py after all routes are registered