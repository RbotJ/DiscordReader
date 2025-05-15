"""
Risk Assessor Module

This module handles risk assessment for options trades, including
position sizing, profit targets, stop losses, and risk/reward calculations.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
import math

from app import app, db
from common.db_models import OptionsContractModel
from common.utils import calculate_risk_reward
from features.management.position_manager import calculate_position_size

# Configure logger
logger = logging.getLogger(__name__)

class TradeRiskAssessor:
    """Class to assess risk for options trades."""
    
    def __init__(self, 
                 max_position_size_percent: float = 2.0,
                 max_account_risk_percent: float = 1.0,
                 max_loss_per_trade_percent: float = 50.0,
                 target_risk_reward_ratio: float = 2.0):
        """Initialize the risk assessor with risk parameters."""
        self.max_position_size_percent = max_position_size_percent
        self.max_account_risk_percent = max_account_risk_percent
        self.max_loss_per_trade_percent = max_loss_per_trade_percent
        self.target_risk_reward_ratio = target_risk_reward_ratio
    
    def get_account_value(self) -> float:
        """Get the current account value."""
        from alpaca.trading.client import TradingClient
        
        api_key = os.environ.get("ALPACA_API_KEY")
        api_secret = os.environ.get("ALPACA_API_SECRET")
        
        if not api_key or not api_secret:
            logger.warning("Alpaca API credentials not found. Using default account value.")
            return 25000.0  # Default value for paper trading
        
        try:
            # Initialize paper trading client
            trading_client = TradingClient(api_key, api_secret, paper=True)
            account = trading_client.get_account()
            return float(account.equity)
        except Exception as e:
            logger.error(f"Error getting account value: {str(e)}")
            return 25000.0  # Default value on error
    
    def calculate_max_position_size(self, option_price: float) -> int:
        """Calculate the maximum position size based on account value."""
        account_value = self.get_account_value()
        
        # Calculate max dollars to allocate to this position
        max_position_dollars = account_value * (self.max_position_size_percent / 100.0)
        
        # Calculate max contracts based on option price
        if option_price <= 0:
            return 0
        
        max_contracts = math.floor(max_position_dollars / (option_price * 100))  # Options are priced per share
        
        return max(1, max_contracts)  # At least 1 contract
    
    def calculate_max_loss_amount(self) -> float:
        """Calculate the maximum dollar amount to risk per trade."""
        account_value = self.get_account_value()
        return account_value * (self.max_account_risk_percent / 100.0)
    
    def calculate_position_size_by_risk(self, 
                                       option_price: float, 
                                       stop_loss_price: float) -> int:
        """Calculate position size based on maximum risk."""
        max_loss_amount = self.calculate_max_loss_amount()
        
        # Calculate loss per contract
        loss_per_contract = (option_price - stop_loss_price) * 100  # Options are for 100 shares
        
        if loss_per_contract <= 0:
            return 1  # Default to 1 contract if stop loss is not below entry
        
        # Calculate max contracts based on risk
        max_contracts = math.floor(max_loss_amount / loss_per_contract)
        
        # Cap based on maximum position size
        max_position_size = self.calculate_max_position_size(option_price)
        
        return min(max(1, max_contracts), max_position_size)  # At least 1, at most max_position_size
    
    def calculate_stop_loss_price(self, option_price: float) -> float:
        """Calculate a stop loss price based on maximum percentage loss."""
        return option_price * (1 - (self.max_loss_per_trade_percent / 100.0))
    
    def calculate_profit_target(self, 
                               option_price: float, 
                               stop_loss_price: float) -> float:
        """Calculate a profit target based on risk/reward ratio."""
        risk = option_price - stop_loss_price
        return option_price + (risk * self.target_risk_reward_ratio)
    
    def assess_trade(self, 
                    symbol: str, 
                    option_contract: Dict[str, Any], 
                    underlying_price: float) -> Dict[str, Any]:
        """
        Assess risk for a potential options trade.
        
        Args:
            symbol: Underlying symbol
            option_contract: Option contract details
            underlying_price: Current price of the underlying
        
        Returns:
            Dictionary with risk assessment data
        """
        option_price = option_contract.get("ask", 0)
        
        if option_price <= 0:
            return {
                "status": "error",
                "message": "Invalid option price"
            }
        
        # Calculate stop loss price
        stop_loss_price = self.calculate_stop_loss_price(option_price)
        
        # Calculate profit target
        profit_target = self.calculate_profit_target(option_price, stop_loss_price)
        
        # Calculate risk/reward ratio
        risk_reward = calculate_risk_reward(option_price, profit_target, stop_loss_price)
        
        # Calculate position size
        position_size = self.calculate_position_size_by_risk(option_price, stop_loss_price)
        
        # Calculate expected values
        max_profit = (profit_target - option_price) * position_size * 100
        max_loss = (option_price - stop_loss_price) * position_size * 100
        
        # Calculate breakeven price
        option_type = option_contract.get("option_type", "call")
        strike_price = option_contract.get("strike", 0)
        
        if option_type.lower() == "call":
            breakeven_price = strike_price + option_price
        else:  # put
            breakeven_price = strike_price - option_price
        
        # Check if breakeven is realistic
        days_to_expiration = (option_contract.get("expiration_date") - date.today()).days
        
        assessment = {
            "symbol": symbol,
            "option_symbol": option_contract.get("symbol"),
            "option_type": option_type,
            "strike": strike_price,
            "expiration_date": option_contract.get("expiration_date").isoformat() if option_contract.get("expiration_date") else None,
            "days_to_expiration": days_to_expiration,
            "underlying_price": underlying_price,
            "option_price": option_price,
            "position_size": position_size,
            "stop_loss_price": stop_loss_price,
            "profit_target": profit_target,
            "risk_reward_ratio": risk_reward,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakeven_price": breakeven_price,
            "delta": option_contract.get("delta"),
            "implied_volatility": option_contract.get("implied_volatility"),
            "assessment": {}
        }
        
        # Qualitative assessment
        assessments = []
        
        # Check risk/reward ratio
        if risk_reward >= self.target_risk_reward_ratio:
            assessments.append({
                "category": "risk_reward",
                "rating": "good",
                "message": f"Risk/reward ratio of {risk_reward:.2f} meets target of {self.target_risk_reward_ratio:.2f}"
            })
        else:
            assessments.append({
                "category": "risk_reward",
                "rating": "poor",
                "message": f"Risk/reward ratio of {risk_reward:.2f} is below target of {self.target_risk_reward_ratio:.2f}"
            })
        
        # Check days to expiration
        if days_to_expiration < 7:
            assessments.append({
                "category": "expiration",
                "rating": "poor",
                "message": f"Only {days_to_expiration} days to expiration - high theta decay risk"
            })
        elif days_to_expiration > 45:
            assessments.append({
                "category": "expiration",
                "rating": "moderate",
                "message": f"{days_to_expiration} days to expiration - slower decay but capital tied up longer"
            })
        else:
            assessments.append({
                "category": "expiration",
                "rating": "good",
                "message": f"{days_to_expiration} days to expiration - balanced time decay"
            })
        
        # Check implied volatility
        iv = option_contract.get("implied_volatility", 0)
        if iv > 0.8:  # 80%
            assessments.append({
                "category": "volatility",
                "rating": "poor",
                "message": f"High implied volatility ({iv:.1%}) - expensive premiums"
            })
        elif iv < 0.2:  # 20%
            assessments.append({
                "category": "volatility",
                "rating": "moderate",
                "message": f"Low implied volatility ({iv:.1%}) - less expensive but potentially less movement"
            })
        else:
            assessments.append({
                "category": "volatility",
                "rating": "good",
                "message": f"Moderate implied volatility ({iv:.1%}) - balanced premium cost"
            })
        
        # Check delta
        delta = abs(option_contract.get("delta", 0))
        if delta < 0.3:
            assessments.append({
                "category": "delta",
                "rating": "poor",
                "message": f"Low delta ({delta:.2f}) - less responsive to price changes"
            })
        elif delta > 0.7:
            assessments.append({
                "category": "delta",
                "rating": "moderate",
                "message": f"High delta ({delta:.2f}) - more expensive but more responsive to price changes"
            })
        else:
            assessments.append({
                "category": "delta",
                "rating": "good",
                "message": f"Moderate delta ({delta:.2f}) - balanced responsiveness to price changes"
            })
        
        # Overall rating
        good_count = sum(1 for a in assessments if a["rating"] == "good")
        poor_count = sum(1 for a in assessments if a["rating"] == "poor")
        
        if poor_count == 0 and good_count >= 2:
            overall_rating = "excellent"
        elif poor_count == 0:
            overall_rating = "good"
        elif poor_count == 1 and good_count >= 1:
            overall_rating = "moderate"
        else:
            overall_rating = "poor"
        
        assessment["assessment"] = {
            "details": assessments,
            "overall_rating": overall_rating
        }
        
        return assessment

def get_risk_parameters() -> Dict[str, float]:
    """Get the current risk parameters."""
    return {
        "max_position_size_percent": 2.0,
        "max_account_risk_percent": 1.0,
        "max_loss_per_trade_percent": 50.0,
        "target_risk_reward_ratio": 2.0
    }

def update_risk_parameters(parameters: Dict[str, float]) -> Dict[str, Any]:
    """Update the risk parameters."""
    # Currently parameters are hardcoded - in a full implementation they would be stored in a database
    return {
        "status": "success",
        "message": "Risk parameters updated",
        "parameters": parameters
    }

def assess_option_trade(symbol: str, option_symbol: str) -> Dict[str, Any]:
    """Assess risk for a potential options trade."""
    # Get the option contract
    option_contract = OptionsContractModel.query.filter_by(symbol=option_symbol).first()
    
    if not option_contract:
        return {
            "status": "error",
            "message": f"Option contract {option_symbol} not found"
        }
    
    # Get the underlying price
    from features.market.client import get_latest_quote
    
    quote = get_latest_quote(symbol)
    if not quote:
        return {
            "status": "error",
            "message": f"Could not get quote for {symbol}"
        }
    
    underlying_price = quote.get("price", 0)
    
    # Convert option contract to dictionary
    option_data = {
        "symbol": option_contract.symbol,
        "underlying": option_contract.underlying,
        "expiration_date": option_contract.expiration_date,
        "strike": option_contract.strike,
        "option_type": option_contract.option_type,
        "bid": option_contract.bid,
        "ask": option_contract.ask,
        "last": option_contract.last,
        "volume": option_contract.volume,
        "open_interest": option_contract.open_interest,
        "implied_volatility": option_contract.implied_volatility,
        "delta": option_contract.delta,
        "gamma": option_contract.gamma,
        "theta": option_contract.theta,
        "vega": option_contract.vega,
        "rho": option_contract.rho
    }
    
    # Create risk assessor with default parameters
    risk_assessor = TradeRiskAssessor()
    
    # Assess the trade
    assessment = risk_assessor.assess_trade(symbol, option_data, underlying_price)
    
    return {
        "status": "success",
        "assessment": assessment
    }

# Register routes for risk assessor
def register_risk_assessor_routes(app):
    from flask import Blueprint, jsonify, request
    
    risk_routes = Blueprint('risk_routes', __name__)
    
    @risk_routes.route('/api/risk/parameters', methods=['GET'])
    def get_risk_parameters_api():
        """Get the current risk parameters."""
        parameters = get_risk_parameters()
        return jsonify(parameters)
    
    @risk_routes.route('/api/risk/parameters', methods=['PUT'])
    def update_risk_parameters_api():
        """Update the risk parameters."""
        parameters = request.json
        result = update_risk_parameters(parameters)
        return jsonify(result)
    
    @risk_routes.route('/api/risk/assess/<symbol>/<option_symbol>', methods=['GET'])
    def assess_trade_api(symbol, option_symbol):
        """Assess risk for a potential options trade."""
        assessment = assess_option_trade(symbol, option_symbol)
        
        if assessment.get("status") == "error":
            return jsonify(assessment), 404
        
        return jsonify(assessment)
    
    @risk_routes.route('/api/risk/position-size', methods=['POST'])
    def calculate_position_size_api():
        """Calculate position size based on risk parameters."""
        data = request.json
        
        price = data.get('price')
        stop_loss = data.get('stop_loss')
        
        if not price or not stop_loss:
            return jsonify({
                "status": "error",
                "message": "Price and stop loss required"
            }), 400
        
        risk_assessor = TradeRiskAssessor()
        position_size = risk_assessor.calculate_position_size_by_risk(float(price), float(stop_loss))
        
        return jsonify({
            "status": "success",
            "position_size": position_size,
            "price": price,
            "stop_loss": stop_loss,
            "max_risk_amount": risk_assessor.calculate_max_loss_amount()
        })
    
    # Register blueprint with app
    app.register_blueprint(risk_routes)
    
    return risk_routes