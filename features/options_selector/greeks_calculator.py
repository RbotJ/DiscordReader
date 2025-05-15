import logging
import math
from datetime import date, datetime
from typing import Dict, List, Optional, Union, Tuple
import numpy as np
from scipy.stats import norm

from common.models import OptionsContract
from common.utils import load_config

# Configure logging
logger = logging.getLogger(__name__)

def calculate_greeks(
    option_type: str,
    underlying_price: float,
    strike_price: float,
    days_to_expiry: float,
    volatility: float,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0
) -> Dict[str, float]:
    """
    Calculate option Greeks using Black-Scholes model
    
    Args:
        option_type: 'call' or 'put'
        underlying_price: Current price of the underlying
        strike_price: Option strike price
        days_to_expiry: Days until expiration
        volatility: Implied volatility (as a decimal, e.g., 0.3 for 30%)
        risk_free_rate: Risk-free interest rate (as a decimal)
        dividend_yield: Continuous dividend yield (as a decimal)
    
    Returns:
        Dictionary containing calculated Greeks (delta, gamma, theta, vega, rho)
    """
    try:
        # Convert days to years
        t = days_to_expiry / 365.0
        
        # Handle expired options
        if t <= 0:
            return {
                "delta": 1.0 if option_type.lower() == "call" and underlying_price > strike_price else 0.0,
                "gamma": 0.0,
                "theta": 0.0,
                "vega": 0.0,
                "rho": 0.0
            }
        
        # Calculate d1 and d2
        d1 = (math.log(underlying_price / strike_price) + 
              (risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * t) / (volatility * math.sqrt(t))
        d2 = d1 - volatility * math.sqrt(t)
        
        # Calculate Greeks based on option type
        if option_type.lower() == "call":
            delta = math.exp(-dividend_yield * t) * norm.cdf(d1)
            theta = (-((underlying_price * volatility * math.exp(-dividend_yield * t)) / 
                     (2 * math.sqrt(t))) * norm.pdf(d1) - 
                     risk_free_rate * strike_price * math.exp(-risk_free_rate * t) * norm.cdf(d2) +
                     dividend_yield * underlying_price * math.exp(-dividend_yield * t) * norm.cdf(d1)) / 365.0
            rho = strike_price * t * math.exp(-risk_free_rate * t) * norm.cdf(d2) / 100.0
        else:  # put
            delta = -math.exp(-dividend_yield * t) * norm.cdf(-d1)
            theta = (-((underlying_price * volatility * math.exp(-dividend_yield * t)) / 
                     (2 * math.sqrt(t))) * norm.pdf(d1) + 
                     risk_free_rate * strike_price * math.exp(-risk_free_rate * t) * norm.cdf(-d2) -
                     dividend_yield * underlying_price * math.exp(-dividend_yield * t) * norm.cdf(-d1)) / 365.0
            rho = -strike_price * t * math.exp(-risk_free_rate * t) * norm.cdf(-d2) / 100.0
        
        # Common Greeks
        gamma = math.exp(-dividend_yield * t) * norm.pdf(d1) / (underlying_price * volatility * math.sqrt(t))
        vega = underlying_price * math.exp(-dividend_yield * t) * norm.pdf(d1) * math.sqrt(t) / 100.0
        
        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "rho": rho
        }
    
    except Exception as e:
        logger.error(f"Error calculating Greeks: {str(e)}")
        return {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0
        }

def calculate_implied_volatility(
    option_type: str,
    option_price: float,
    underlying_price: float,
    strike_price: float,
    days_to_expiry: float,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate implied volatility using bisection method
    
    Args:
        option_type: 'call' or 'put'
        option_price: Market price of the option
        underlying_price: Current price of the underlying
        strike_price: Option strike price
        days_to_expiry: Days until expiration
        risk_free_rate: Risk-free interest rate (as a decimal)
    
    Returns:
        Implied volatility as a decimal (e.g., 0.3 for 30%)
    """
    try:
        # Convert days to years
        t = days_to_expiry / 365.0
        
        # Handle expired options
        if t <= 0:
            return 0.0
        
        # Initial guesses
        low_vol = 0.001
        high_vol = 5.0
        
        # Tolerance
        epsilon = 0.0001
        
        # Maximum iterations
        max_iterations = 100
        
        # Bisection method
        for _ in range(max_iterations):
            mid_vol = (low_vol + high_vol) / 2.0
            
            # Calculate option price with mid_vol
            greeks = calculate_greeks(
                option_type=option_type,
                underlying_price=underlying_price,
                strike_price=strike_price,
                days_to_expiry=days_to_expiry,
                volatility=mid_vol,
                risk_free_rate=risk_free_rate
            )
            
            # Calculate price based on Black-Scholes
            if option_type.lower() == "call":
                d1 = (math.log(underlying_price / strike_price) + 
                     (risk_free_rate + 0.5 * mid_vol ** 2) * t) / (mid_vol * math.sqrt(t))
                d2 = d1 - mid_vol * math.sqrt(t)
                calculated_price = underlying_price * norm.cdf(d1) - strike_price * math.exp(-risk_free_rate * t) * norm.cdf(d2)
            else:  # put
                d1 = (math.log(underlying_price / strike_price) + 
                     (risk_free_rate + 0.5 * mid_vol ** 2) * t) / (mid_vol * math.sqrt(t))
                d2 = d1 - mid_vol * math.sqrt(t)
                calculated_price = strike_price * math.exp(-risk_free_rate * t) * norm.cdf(-d2) - underlying_price * norm.cdf(-d1)
            
            # Check if we're close enough
            if abs(calculated_price - option_price) < epsilon:
                return mid_vol
            
            # Adjust bounds
            if calculated_price > option_price:
                high_vol = mid_vol
            else:
                low_vol = mid_vol
        
        # Return best guess after max iterations
        return (low_vol + high_vol) / 2.0
    
    except Exception as e:
        logger.error(f"Error calculating implied volatility: {str(e)}")
        return 0.3  # Default fallback

def update_contract_greeks(contract: OptionsContract, underlying_price: float) -> OptionsContract:
    """
    Update Greeks for an option contract
    
    Args:
        contract: OptionsContract object
        underlying_price: Current price of the underlying
    
    Returns:
        Updated OptionsContract object with refreshed Greeks
    """
    try:
        # Calculate days to expiry
        today = date.today()
        days_to_expiry = (contract.expiration - today).days
        
        # Use mid price
        option_price = (contract.bid + contract.ask) / 2.0
        if option_price <= 0:
            option_price = contract.last
        
        # If we don't have IV, calculate it
        if contract.implied_volatility <= 0:
            contract.implied_volatility = calculate_implied_volatility(
                option_type=contract.option_type,
                option_price=option_price,
                underlying_price=underlying_price,
                strike_price=contract.strike,
                days_to_expiry=days_to_expiry
            )
        
        # Calculate Greeks
        greeks = calculate_greeks(
            option_type=contract.option_type,
            underlying_price=underlying_price,
            strike_price=contract.strike,
            days_to_expiry=days_to_expiry,
            volatility=contract.implied_volatility
        )
        
        # Update the contract
        contract.delta = greeks["delta"]
        contract.gamma = greeks["gamma"]
        contract.theta = greeks["theta"]
        contract.vega = greeks["vega"]
        contract.rho = greeks["rho"]
        
        return contract
    
    except Exception as e:
        logger.error(f"Error updating contract Greeks: {str(e)}")
        return contract
