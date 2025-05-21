import logging
import requests
import threading
import time
import math
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from flask import Blueprint, jsonify, request, current_app
from alpaca.trading import TradingClient
from alpaca.data import StockHistoricalDataClient
from common.models import OptionsContract
from common.events import get_database_connection, cache_data as store_in_cache, get_from_cache

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint
options_routes = Blueprint('options', __name__, url_prefix='/api/options')

# Cache for options chains
options_cache: Dict[str, Dict[str, Any]] = {}
# Cache expiration time (in seconds)
CACHE_EXPIRY = 300  # 5 minutes


def initialize_alpaca_client():
    """Initialize Alpaca API client."""
    api_key = current_app.config.get("ALPACA_API_KEY", "")
    api_secret = current_app.config.get("ALPACA_API_SECRET", "")
    
    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set. Options features will not work.")
        return None, None
    
    try:
        # Initialize trading client
        trading_client = TradingClient(api_key, api_secret, paper=True)
        
        # Initialize historical data client
        historical_client = StockHistoricalDataClient(api_key, api_secret)
        
        return trading_client, historical_client
    except Exception as e:
        logger.error(f"Error initializing Alpaca client: {str(e)}", exc_info=True)
        return None, None


def fetch_options_chain(symbol: str, expiration_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch options chain data for a given symbol and expiration date.
    Uses an external API (Polygon.io) due to Alpaca limitations for options data.
    
    Note: In production, this would be replaced with a direct Polygon.io subscription.
    """
    # Check if we have a cached chain that's still valid using PostgreSQL cache
    cache_key = f"options_chain:{symbol}_{expiration_date or 'all'}"
    
    cached_data = get_from_cache(cache_key)
    if cached_data:
        logger.debug(f"Using cached options chain for {cache_key}")
        return cached_data
    
    # For demonstration purposes, we'll construct a synthetic options chain
    # In production, this would call the Polygon.io API
    
    # Get the current stock price
    trading_client, _ = initialize_alpaca_client()
    
    if not trading_client:
        logger.error("Trading client not initialized")
        return {"error": "Trading client not initialized"}
    
    try:
        # Get last trade price
        stock_info = trading_client.get_stock_positions()
        current_price = None
        
        for position in stock_info:
            if position.symbol == symbol:
                current_price = float(position.current_price)
                break
        
        if not current_price:
            # Try to get the current price from the latest quote
            import requests
            response = requests.get(f"http://localhost:5000/api/market/prices?symbols={symbol}")
            if response.status_code == 200:
                data = response.json()
                current_price = data.get('prices', {}).get(symbol)
        
        if not current_price:
            # Fallback to a reasonable default for demo
            current_price = 100.0
        
        # Generate expirations (every Friday for next 4 weeks)
        today = date.today()
        days_to_friday = (4 - today.weekday()) % 7  # 4 = Friday
        
        expirations = []
        for i in range(4):  # 4 weeks
            expiry = today + timedelta(days=days_to_friday + i*7)
            expirations.append(expiry.strftime("%Y-%m-%d"))
        
        # Filter by expiration date if provided
        if expiration_date:
            if expiration_date in expirations:
                expirations = [expiration_date]
            else:
                return {"error": f"Expiration date {expiration_date} not available"}
        
        # Generate strike prices around the current price
        atm_strike = round(current_price / 5) * 5  # Round to nearest $5
        strikes = [atm_strike + (i * 5) for i in range(-5, 6)]  # -25 to +25 from ATM
        
        # Calculate options chain
        chain = {
            "symbol": symbol,
            "underlying_price": current_price,
            "timestamp": datetime.now().isoformat(),
            "expirations": expirations,
            "chains": {}
        }
        
        for exp in expirations:
            days_to_expiry = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
            
            # Skip if expiry is in the past
            if days_to_expiry < 0:
                continue
            
            chain["chains"][exp] = {"calls": [], "puts": []}
            
            for strike in strikes:
                # Calculate theoretical values for demonstration
                # In production, these would come from the actual market data
                
                # Simple Black-Scholes approximation
                iv = 0.3  # 30% implied volatility as baseline
                
                # Adjust IV based on distance from current price (smile effect)
                distance_pct = abs(strike - current_price) / current_price
                iv_adjustment = distance_pct * 0.2  # Increase IV by up to 20% at edges
                
                iv_call = iv + iv_adjustment
                iv_put = iv + iv_adjustment
                
                # Calculate simple delta approximation
                moneyness = current_price / strike
                
                # Simplified delta calculation
                call_delta = max(0.01, min(0.99, 0.5 + 0.5 * (1 - 2 / (1 + math.exp(2 * (moneyness - 1) / (iv_call * math.sqrt(days_to_expiry/365)))))))
                put_delta = max(0.01, min(0.99, 1 - call_delta))
                
                # Negative delta for puts
                put_delta = -put_delta
                
                # Approximate pricing using delta and other factors
                atm_premium = current_price * iv * math.sqrt(days_to_expiry/365) / 4
                
                call_price = max(0.01, atm_premium * call_delta * 2)
                put_price = max(0.01, atm_premium * abs(put_delta) * 2)
                
                # Adjust for intrinsic value
                call_intrinsic = max(0, current_price - strike)
                put_intrinsic = max(0, strike - current_price)
                
                call_price = max(call_price, call_intrinsic + 0.01)
                put_price = max(put_price, put_intrinsic + 0.01)
                
                # Create the call option
                call = OptionsContract(
                    symbol=f"{symbol}_{exp.replace('-', '')}C{int(strike)}",
                    underlying=symbol,
                    expiration_date=datetime.strptime(exp, "%Y-%m-%d").date(),
                    strike=strike,
                    option_type="call",
                    bid=round(call_price * 0.95, 2),
                    ask=round(call_price * 1.05, 2),
                    last=round(call_price, 2),
                    volume=int(100 * (1 - abs(0.5 - call_delta))),
                    open_interest=int(500 * (1 - abs(0.5 - call_delta))),
                    implied_volatility=round(iv_call, 3),
                    delta=round(call_delta, 3),
                    gamma=round(call_delta * (1 - call_delta) / (current_price * iv_call * math.sqrt(days_to_expiry/365)), 3),
                    theta=round(-call_price / days_to_expiry, 3),
                    vega=round(current_price * math.sqrt(days_to_expiry/365) * 0.01, 3),
                    rho=round(strike * days_to_expiry / 365 * 0.01, 3)
                ).dict()
                
                # Create the put option
                put = OptionsContract(
                    symbol=f"{symbol}_{exp.replace('-', '')}P{int(strike)}",
                    underlying=symbol,
                    expiration_date=datetime.strptime(exp, "%Y-%m-%d").date(),
                    strike=strike,
                    option_type="put",
                    bid=round(put_price * 0.95, 2),
                    ask=round(put_price * 1.05, 2),
                    last=round(put_price, 2),
                    volume=int(100 * (1 - abs(0.5 - abs(put_delta)))),
                    open_interest=int(500 * (1 - abs(0.5 - abs(put_delta)))),
                    implied_volatility=round(iv_put, 3),
                    delta=round(put_delta, 3),
                    gamma=round(abs(put_delta) * (1 - abs(put_delta)) / (current_price * iv_put * math.sqrt(days_to_expiry/365)), 3),
                    theta=round(-put_price / days_to_expiry, 3),
                    vega=round(current_price * math.sqrt(days_to_expiry/365) * 0.01, 3),
                    rho=round(-strike * days_to_expiry / 365 * 0.01, 3)
                ).dict()
                
                chain["chains"][exp]["calls"].append(call)
                chain["chains"][exp]["puts"].append(put)
        
        # Cache the result in PostgreSQL
        store_in_cache(cache_key.replace("options_chain:", ""), chain, CACHE_EXPIRY)
        
        return chain
        
    except Exception as e:
        logger.error(f"Error fetching options chain for {symbol}: {str(e)}", exc_info=True)
        return {"error": str(e)}


def get_best_options_for_direction(
    symbol: str,
    direction: str,
    expiration_date: Optional[str] = None,
    max_delta: float = 0.7,
    min_delta: float = 0.3,
    min_volume: int = 10,
    max_spread_pct: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Get the best options contracts for a given direction (bullish/bearish).
    
    Args:
        symbol: The ticker symbol
        direction: 'bullish' or 'bearish'
        expiration_date: Optional expiration date filter
        max_delta: Maximum absolute delta value (default 0.7)
        min_delta: Minimum absolute delta value (default 0.3)
        min_volume: Minimum trading volume
        max_spread_pct: Maximum bid-ask spread as percentage of option price
    
    Returns:
        List of filtered options contracts
    """
    # Get the options chain
    chain = fetch_options_chain(symbol, expiration_date)
    
    if "error" in chain:
        logger.error(f"Error getting options chain: {chain['error']}")
        return []
    
    filtered_options = []
    
    # For each expiration date in the chain
    for exp, exp_data in chain.get("chains", {}).items():
        # For bullish signals, we want calls; for bearish, we want puts
        option_type = "calls" if direction.lower() == "bullish" else "puts"
        
        for option in exp_data.get(option_type, []):
            # Calculate absolute delta
            abs_delta = abs(option.get("delta", 0))
            
            # Calculate spread percentage
            ask = option.get("ask", 0)
            bid = option.get("bid", 0)
            if ask <= 0:
                spread_pct = 1.0  # 100% spread (avoid division by zero)
            else:
                spread_pct = (ask - bid) / ask
            
            # Apply filters
            if (min_delta <= abs_delta <= max_delta and
                option.get("volume", 0) >= min_volume and
                spread_pct <= max_spread_pct):
                
                # Add the option to our filtered list
                option["expiration"] = exp
                filtered_options.append(option)
    
    # Sort by delta (closest to 0.5 for balanced risk/reward)
    filtered_options.sort(key=lambda x: abs(abs(x.get("delta", 0)) - 0.5))
    
    return filtered_options


@options_routes.route('/chain/<symbol>', methods=['GET'])
def get_options_chain(symbol):
    """Get options chain for a symbol."""
    try:
        symbol = symbol.upper()
        
        # Get query parameters
        expiration = request.args.get('expiration')
        
        # Fetch the chain
        chain = fetch_options_chain(symbol, expiration)
        
        if "error" in chain:
            return jsonify({"status": "error", "message": chain["error"]}), 400
        
        return jsonify({
            "status": "success",
            "data": chain
        })
        
    except Exception as e:
        logger.error(f"Error getting options chain: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@options_routes.route('/filter/<symbol>', methods=['GET'])
def filter_options(symbol):
    """Filter options based on criteria."""
    try:
        symbol = symbol.upper()
        
        # Get query parameters
        direction = request.args.get('direction', 'bullish')
        expiration = request.args.get('expiration')
        min_delta = float(request.args.get('min_delta', 0.3))
        max_delta = float(request.args.get('max_delta', 0.7))
        min_volume = int(request.args.get('min_volume', 10))
        max_spread_pct = float(request.args.get('max_spread', 0.15))
        
        if direction not in ['bullish', 'bearish']:
            return jsonify({
                "status": "error",
                "message": "Direction must be 'bullish' or 'bearish'"
            }), 400
        
        # Get filtered options
        options = get_best_options_for_direction(
            symbol,
            direction,
            expiration,
            max_delta,
            min_delta,
            min_volume,
            max_spread_pct
        )
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "direction": direction,
            "count": len(options),
            "options": options
        })
        
    except Exception as e:
        logger.error(f"Error filtering options: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@options_routes.route('/recommend/<symbol>', methods=['GET'])
def recommend_option(symbol):
    """Recommend the best option for a given signal."""
    try:
        symbol = symbol.upper()
        
        # Get query parameters
        direction = request.args.get('direction', 'bullish')
        signal_id = request.args.get('signal_id')
        
        # If signal_id provided, look up the signal
        if signal_id:
            # Make request to strategy API to get signal details
            import requests
            response = requests.get(f"http://localhost:5000/api/strategy/signals/{signal_id}")
            
            if response.status_code == 200:
                signal_data = response.json().get('signal', {})
                symbol = signal_data.get('symbol', symbol)
                
                # Determine direction from signal category
                category = signal_data.get('category', '')
                if category in ['breakout', 'bounce']:
                    direction = 'bullish'
                elif category in ['breakdown', 'rejection']:
                    direction = 'bearish'
        
        # Get expiration 2-3 weeks out for balanced theta decay
        today = date.today()
        days_to_friday = (4 - today.weekday()) % 7
        
        # Try to get the Friday 2 weeks out
        target_expiry = today + timedelta(days=days_to_friday + 7)
        expiration = target_expiry.strftime("%Y-%m-%d")
        
        # Get filtered options with reasonable delta range
        options = get_best_options_for_direction(
            symbol,
            direction,
            expiration,
            max_delta=0.6,
            min_delta=0.4,  # Near 0.5 delta for balanced risk/reward
            min_volume=20,
            max_spread_pct=0.1
        )
        
        if not options:
            # Try without expiration filter
            options = get_best_options_for_direction(
                symbol,
                direction,
                max_delta=0.6,
                min_delta=0.4,
                min_volume=10,
                max_spread_pct=0.15
            )
        
        if not options:
            return jsonify({
                "status": "error",
                "message": f"No suitable options found for {symbol} {direction}"
            }), 404
        
        # Get the best option (first in the list, sorted by delta proximity to 0.5)
        best_option = options[0]
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "direction": direction,
            "recommendation": best_option,
            "alternatives": options[1:5] if len(options) > 1 else []
        })
        
    except Exception as e:
        logger.error(f"Error recommending option: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
