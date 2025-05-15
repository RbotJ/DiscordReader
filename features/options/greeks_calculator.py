"""
Options Greeks Calculator Module

This module implements the Black-Scholes model for calculating
option Greeks (Delta, Gamma, Theta, Vega, and Rho).
"""

import os
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
import numpy as np
from scipy.stats import norm

from app import app, db
from common.db_models import OptionsContractModel

# Configure logger
logger = logging.getLogger(__name__)

def calculate_days_to_expiration(expiration_date: date) -> int:
    """Calculate the number of days to expiration for an option."""
    return (expiration_date - date.today()).days

def calculate_time_to_expiration(days_to_expiration: int) -> float:
    """Convert days to expiration to years."""
    return days_to_expiration / 365.0

def calculate_black_scholes(
    option_type: str,
    spot_price: float,
    strike_price: float,
    time_to_expiration: float,
    risk_free_rate: float,
    volatility: float
) -> Dict[str, float]:
    """
    Calculate option price and Greeks using the Black-Scholes model.
    
    Args:
        option_type: 'call' or 'put'
        spot_price: Current price of the underlying asset
        strike_price: Strike price of the option
        time_to_expiration: Time to expiration in years
        risk_free_rate: Annual risk-free interest rate (decimal)
        volatility: Implied volatility (decimal)
    
    Returns:
        Dictionary containing option price and Greeks
    """
    if time_to_expiration <= 0:
        return {
            "price": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0
        }
    
    option_type = option_type.lower()
    
    # Calculate d1 and d2
    d1 = (math.log(spot_price / strike_price) + 
          (risk_free_rate + 0.5 * volatility**2) * time_to_expiration) / (volatility * math.sqrt(time_to_expiration))
    d2 = d1 - volatility * math.sqrt(time_to_expiration)
    
    # Calculate option price
    if option_type == 'call':
        price = spot_price * norm.cdf(d1) - strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(d2)
    else:  # put
        price = strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(-d2) - spot_price * norm.cdf(-d1)
    
    # Calculate Greeks
    # Delta
    if option_type == 'call':
        delta = norm.cdf(d1)
    else:  # put
        delta = norm.cdf(d1) - 1
    
    # Gamma (same for both call and put)
    gamma = norm.pdf(d1) / (spot_price * volatility * math.sqrt(time_to_expiration))
    
    # Theta (annualized)
    if option_type == 'call':
        theta = -spot_price * norm.pdf(d1) * volatility / (2 * math.sqrt(time_to_expiration)) - \
                risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(d2)
    else:  # put
        theta = -spot_price * norm.pdf(d1) * volatility / (2 * math.sqrt(time_to_expiration)) + \
                risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(-d2)
    
    # Convert to daily theta (market convention)
    theta = theta / 365.0
    
    # Vega (for 1% change in volatility)
    vega = 0.01 * spot_price * math.sqrt(time_to_expiration) * norm.pdf(d1)
    
    # Rho (for 1% change in interest rate)
    if option_type == 'call':
        rho = 0.01 * strike_price * time_to_expiration * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(d2)
    else:  # put
        rho = -0.01 * strike_price * time_to_expiration * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(-d2)
    
    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "rho": rho
    }

def calculate_implied_volatility(
    option_type: str,
    option_price: float,
    spot_price: float,
    strike_price: float,
    time_to_expiration: float,
    risk_free_rate: float,
    max_iterations: int = 100,
    precision: float = 0.00001
) -> float:
    """
    Calculate the implied volatility of an option using an iterative method.
    
    Args:
        option_type: 'call' or 'put'
        option_price: Market price of the option
        spot_price: Current price of the underlying asset
        strike_price: Strike price of the option
        time_to_expiration: Time to expiration in years
        risk_free_rate: Annual risk-free interest rate (decimal)
        max_iterations: Maximum number of iterations for the solver
        precision: Desired precision of the result
    
    Returns:
        Implied volatility as a decimal
    """
    option_type = option_type.lower()
    
    # Initial guesses for volatility
    vol_low = 0.001
    vol_high = 5.0
    
    # Check if option price is valid
    if option_price <= 0:
        return 0.0
    
    # Calculate option price for low volatility
    price_low = calculate_black_scholes(
        option_type, spot_price, strike_price, time_to_expiration, risk_free_rate, vol_low
    )["price"]
    
    # Calculate option price for high volatility
    price_high = calculate_black_scholes(
        option_type, spot_price, strike_price, time_to_expiration, risk_free_rate, vol_high
    )["price"]
    
    # Check if option price is outside the bounds
    if option_price <= price_low:
        return vol_low
    if option_price >= price_high:
        return vol_high
    
    # Iterative solver using bisection method
    for _ in range(max_iterations):
        vol_mid = (vol_low + vol_high) / 2.0
        price_mid = calculate_black_scholes(
            option_type, spot_price, strike_price, time_to_expiration, risk_free_rate, vol_mid
        )["price"]
        
        if abs(price_mid - option_price) < precision:
            return vol_mid
        
        if price_mid < option_price:
            vol_low = vol_mid
        else:
            vol_high = vol_mid
    
    # Return the best estimate after max iterations
    return (vol_low + vol_high) / 2.0

def calculate_greek_exposure(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate the portfolio's exposure to various Greeks.
    
    Args:
        positions: List of position dictionaries
    
    Returns:
        Dictionary of total Greek exposures
    """
    # Initialize exposure values
    exposures = {
        "delta": 0.0,
        "gamma": 0.0,
        "theta": 0.0,
        "vega": 0.0,
        "rho": 0.0
    }
    
    # Iterate through positions
    for position in positions:
        symbol = position.get("symbol", "")
        quantity = position.get("quantity", 0)
        
        # Skip if not an options position
        if " " not in symbol:
            continue
        
        # Get the option contract
        option_contract = OptionsContractModel.query.filter_by(symbol=symbol).first()
        if not option_contract:
            continue
        
        # Accumulate weighted Greeks
        exposures["delta"] += (option_contract.delta or 0.0) * quantity
        exposures["gamma"] += (option_contract.gamma or 0.0) * quantity
        exposures["theta"] += (option_contract.theta or 0.0) * quantity
        exposures["vega"] += (option_contract.vega or 0.0) * quantity
        exposures["rho"] += (option_contract.rho or 0.0) * quantity
    
    return exposures

def update_option_greeks(option_id: int, market_price: float) -> bool:
    """
    Update the Greeks for an option contract based on the current market price.
    
    Args:
        option_id: ID of the option contract
        market_price: Current market price of the underlying
    
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Get the option contract
        option = OptionsContractModel.query.get(option_id)
        if not option:
            logger.error(f"Option with ID {option_id} not found")
            return False
        
        # Calculate days to expiration
        days_to_exp = calculate_days_to_expiration(option.expiration_date)
        if days_to_exp <= 0:
            # Option has expired
            logger.info(f"Option {option.symbol} has expired, skipping Greeks calculation")
            return False
        
        # Calculate time to expiration in years
        time_to_exp = calculate_time_to_expiration(days_to_exp)
        
        # Use mid price of the option for implied volatility calculation
        option_price = (option.bid + option.ask) / 2.0 if option.bid and option.ask else option.last
        
        # Use a standard risk-free rate (adjust as needed)
        risk_free_rate = 0.03  # 3%
        
        # Calculate implied volatility
        implied_vol = calculate_implied_volatility(
            option.option_type,
            option_price,
            market_price,
            option.strike,
            time_to_exp,
            risk_free_rate
        )
        
        # Calculate Greeks
        greeks = calculate_black_scholes(
            option.option_type,
            market_price,
            option.strike,
            time_to_exp,
            risk_free_rate,
            implied_vol
        )
        
        # Update option contract with calculated Greeks
        option.implied_volatility = implied_vol
        option.delta = greeks["delta"]
        option.gamma = greeks["gamma"]
        option.theta = greeks["theta"]
        option.vega = greeks["vega"]
        option.rho = greeks["rho"]
        
        # Save changes
        db.session.commit()
        
        logger.debug(f"Updated Greeks for {option.symbol}: IV={implied_vol:.4f}, Delta={greeks['delta']:.4f}")
        return True
    except Exception as e:
        logger.error(f"Error updating option Greeks: {str(e)}")
        db.session.rollback()
        return False

def update_all_options_greeks() -> Tuple[int, int]:
    """
    Update Greeks for all options contracts in the database.
    
    Returns:
        Tuple of (total options, successfully updated)
    """
    from features.market.client import get_latest_quotes
    
    # Get all unique underlying symbols
    underlyings = db.session.query(OptionsContractModel.underlying).distinct().all()
    underlying_symbols = [u[0] for u in underlyings]
    
    # Get latest market prices for all underlyings
    market_prices = {}
    if underlying_symbols:
        quotes = get_latest_quotes(underlying_symbols)
        
        for symbol, quote in quotes.items():
            if quote:
                market_prices[symbol] = quote.get("price")
    
    # Get all active options (not expired)
    today = date.today()
    active_options = OptionsContractModel.query.filter(OptionsContractModel.expiration_date >= today).all()
    
    total_options = len(active_options)
    successful_updates = 0
    
    # Update Greeks for each option
    for option in active_options:
        market_price = market_prices.get(option.underlying)
        if market_price:
            success = update_option_greeks(option.id, market_price)
            if success:
                successful_updates += 1
    
    logger.info(f"Updated Greeks for {successful_updates} of {total_options} options")
    return total_options, successful_updates

# Register routes for Greeks calculator
def register_greeks_routes(app):
    from flask import Blueprint, jsonify, request
    
    greeks_routes = Blueprint('greeks_routes', __name__)
    
    @greeks_routes.route('/api/options/greeks/calculate', methods=['POST'])
    def calculate_greeks_api():
        """Calculate option Greeks using the Black-Scholes model."""
        data = request.json
        
        option_type = data.get('option_type', 'call')
        spot_price = data.get('spot_price')
        strike_price = data.get('strike_price')
        days_to_expiration = data.get('days_to_expiration')
        volatility = data.get('volatility')
        risk_free_rate = data.get('risk_free_rate', 0.03)
        
        if not all([spot_price, strike_price, days_to_expiration, volatility]):
            return jsonify({
                "status": "error",
                "message": "Missing required parameters"
            }), 400
        
        # Convert to correct types
        spot_price = float(spot_price)
        strike_price = float(strike_price)
        days_to_expiration = int(days_to_expiration)
        volatility = float(volatility) / 100.0  # Convert from percentage
        risk_free_rate = float(risk_free_rate) / 100.0  # Convert from percentage
        
        # Calculate time to expiration in years
        time_to_exp = calculate_time_to_expiration(days_to_expiration)
        
        # Calculate Greeks
        greeks = calculate_black_scholes(
            option_type,
            spot_price,
            strike_price,
            time_to_exp,
            risk_free_rate,
            volatility
        )
        
        return jsonify({
            "status": "success",
            "greeks": greeks
        })
    
    @greeks_routes.route('/api/options/greeks/implied-volatility', methods=['POST'])
    def calculate_implied_volatility_api():
        """Calculate implied volatility for an option."""
        data = request.json
        
        option_type = data.get('option_type', 'call')
        option_price = data.get('option_price')
        spot_price = data.get('spot_price')
        strike_price = data.get('strike_price')
        days_to_expiration = data.get('days_to_expiration')
        risk_free_rate = data.get('risk_free_rate', 0.03)
        
        if not all([option_price, spot_price, strike_price, days_to_expiration]):
            return jsonify({
                "status": "error",
                "message": "Missing required parameters"
            }), 400
        
        # Convert to correct types
        option_price = float(option_price)
        spot_price = float(spot_price)
        strike_price = float(strike_price)
        days_to_expiration = int(days_to_expiration)
        risk_free_rate = float(risk_free_rate) / 100.0  # Convert from percentage
        
        # Calculate time to expiration in years
        time_to_exp = calculate_time_to_expiration(days_to_expiration)
        
        # Calculate implied volatility
        implied_vol = calculate_implied_volatility(
            option_type,
            option_price,
            spot_price,
            strike_price,
            time_to_exp,
            risk_free_rate
        )
        
        return jsonify({
            "status": "success",
            "implied_volatility": implied_vol,
            "implied_volatility_percent": implied_vol * 100.0
        })
    
    @greeks_routes.route('/api/options/greeks/exposure', methods=['GET'])
    def get_greek_exposure_api():
        """Get the current Greek exposure for the portfolio."""
        from features.management.position_manager import get_all_positions
        
        positions = get_all_positions()
        exposures = calculate_greek_exposure(positions)
        
        return jsonify({
            "status": "success",
            "exposures": exposures
        })
    
    @greeks_routes.route('/api/options/greeks/update', methods=['POST'])
    def update_greeks_api():
        """Update Greeks for all options."""
        total, successful = update_all_options_greeks()
        
        return jsonify({
            "status": "success",
            "total_options": total,
            "updated_options": successful,
            "success_rate": f"{(successful / total * 100) if total else 0:.2f}%"
        })
    
    # Register blueprint with app
    app.register_blueprint(greeks_routes)
    
    return greeks_routes