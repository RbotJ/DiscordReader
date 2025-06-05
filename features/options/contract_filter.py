"""
Options Contract Filter Module

This module implements filtering mechanisms for options contracts
based on various criteria such as delta, expiration, volume, and
open interest.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta, date
import math

from flask import current_app
from common.db import db
from common.db_models import OptionsContractModel
from common.events import publish_event, get_events
from common.events.constants import EventTypes

# Configure logger
logger = logging.getLogger(__name__)

class OptionsFilter:
    """Base class for options contract filters."""
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter the list of contracts based on specific criteria."""
        raise NotImplementedError("Subclasses must implement filter method")

class DeltaFilter(OptionsFilter):
    """Filter options contracts based on delta value."""
    def __init__(self, min_delta: float = 0.2, max_delta: float = 0.8):
        self.min_delta = min_delta
        self.max_delta = max_delta
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on delta value."""
        return [
            contract for contract in contracts
            if contract.get("delta") is not None and
            abs(float(contract.get("delta", 0))) >= self.min_delta and
            abs(float(contract.get("delta", 0))) <= self.max_delta
        ]

class ExpirationFilter(OptionsFilter):
    """Filter options contracts based on days to expiration."""
    def __init__(self, min_days: int = 7, max_days: int = 45):
        self.min_days = min_days
        self.max_days = max_days
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on days to expiration."""
        today = date.today()
        return [
            contract for contract in contracts
            if contract.get("expiration_date") and
            (contract["expiration_date"] - today).days >= self.min_days and
            (contract["expiration_date"] - today).days <= self.max_days
        ]

class VolumeFilter(OptionsFilter):
    """Filter options contracts based on trading volume."""
    def __init__(self, min_volume: int = 100):
        self.min_volume = min_volume
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on trading volume."""
        return [
            contract for contract in contracts
            if contract.get("volume") is not None and
            int(contract.get("volume", 0)) >= self.min_volume
        ]

class OpenInterestFilter(OptionsFilter):
    """Filter options contracts based on open interest."""
    def __init__(self, min_open_interest: int = 100):
        self.min_open_interest = min_open_interest
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on open interest."""
        return [
            contract for contract in contracts
            if contract.get("open_interest") is not None and
            int(contract.get("open_interest", 0)) >= self.min_open_interest
        ]

class SpreadFilter(OptionsFilter):
    """Filter options contracts based on bid-ask spread."""
    def __init__(self, max_spread_percent: float = 10.0):
        self.max_spread_percent = max_spread_percent
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on bid-ask spread."""
        return [
            contract for contract in contracts
            if contract.get("bid") is not None and
            contract.get("ask") is not None and
            contract.get("bid") > 0 and
            ((contract.get("ask") - contract.get("bid")) / contract.get("bid") * 100) <= self.max_spread_percent
        ]

class ImpliedVolatilityFilter(OptionsFilter):
    """Filter options contracts based on implied volatility."""
    def __init__(self, min_iv: float = 0.2, max_iv: float = 1.0):
        self.min_iv = min_iv
        self.max_iv = max_iv
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on implied volatility."""
        return [
            contract for contract in contracts
            if contract.get("implied_volatility") is not None and
            float(contract.get("implied_volatility", 0)) >= self.min_iv and
            float(contract.get("implied_volatility", 0)) <= self.max_iv
        ]

class PriceFilter(OptionsFilter):
    """Filter options contracts based on price."""
    def __init__(self, min_price: float = 0.1, max_price: float = 5.0):
        self.min_price = min_price
        self.max_price = max_price
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on price."""
        return [
            contract for contract in contracts
            if contract.get("ask") is not None and
            float(contract.get("ask", 0)) >= self.min_price and
            float(contract.get("ask", 0)) <= self.max_price
        ]

class OptionTypeFilter(OptionsFilter):
    """Filter options contracts based on option type (call/put)."""
    def __init__(self, option_type: str = "call"):
        self.option_type = option_type.lower()
    
    def filter(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter contracts based on option type."""
        return [
            contract for contract in contracts
            if contract.get("option_type") and
            contract.get("option_type").lower() == self.option_type
        ]

class ContractFilterChain:
    """Chain of filters to apply to options contracts."""
    def __init__(self, filters: List[OptionsFilter] = None):
        self.filters = filters or []
    
    def add_filter(self, filter_obj: OptionsFilter):
        """Add a filter to the chain."""
        self.filters.append(filter_obj)
    
    def apply_filters(self, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all filters in sequence."""
        filtered_contracts = contracts
        for filter_obj in self.filters:
            filtered_contracts = filter_obj.filter(filtered_contracts)
        return filtered_contracts

def create_directional_filter_chain(direction: str, option_type: str = None) -> ContractFilterChain:
    """Create a filter chain for directional trades."""
    filter_chain = ContractFilterChain()
    
    # Add common filters
    filter_chain.add_filter(ExpirationFilter(min_days=7, max_days=45))
    filter_chain.add_filter(VolumeFilter(min_volume=50))
    filter_chain.add_filter(OpenInterestFilter(min_open_interest=50))
    filter_chain.add_filter(SpreadFilter(max_spread_percent=15.0))
    
    # Determine option type based on direction if not specified
    if option_type is None:
        option_type = "call" if direction.lower() == "bullish" else "put"
    
    filter_chain.add_filter(OptionTypeFilter(option_type=option_type))
    
    # Set appropriate delta range based on direction
    if direction.lower() == "bullish":
        filter_chain.add_filter(DeltaFilter(min_delta=0.3, max_delta=0.7))
    else:  # bearish
        filter_chain.add_filter(DeltaFilter(min_delta=0.3, max_delta=0.7))
    
    return filter_chain

def rank_contracts(contracts: List[Dict[str, Any]], direction: str) -> List[Dict[str, Any]]:
    """Rank filtered contracts by desirability for a given direction."""
    if not contracts:
        return []
    
    # Calculate a score for each contract
    for contract in contracts:
        score = 0
        
        # Delta score - prefer higher delta for directional trades, but not too high
        delta = abs(float(contract.get("delta", 0)))
        delta_score = 0
        if 0.4 <= delta <= 0.6:
            delta_score = 10
        elif 0.3 <= delta < 0.4 or 0.6 < delta <= 0.7:
            delta_score = 7
        else:
            delta_score = 3
        score += delta_score
        
        # Volume and open interest score - prefer more liquid contracts
        volume = int(contract.get("volume", 0))
        open_interest = int(contract.get("open_interest", 0))
        liquidity_score = min(10, max(1, int((volume + open_interest) / 100)))
        score += liquidity_score
        
        # Bid-ask spread score - prefer tighter spreads
        bid = float(contract.get("bid", 0))
        ask = float(contract.get("ask", 0))
        if bid > 0:
            spread_percent = (ask - bid) / bid * 100
            spread_score = max(1, 10 - int(spread_percent))
            score += spread_score
        
        # Days to expiration score - prefer middle-term options
        if contract.get("expiration_date"):
            days_to_expiration = (contract["expiration_date"] - date.today()).days
            if 20 <= days_to_expiration <= 40:
                expiry_score = 10
            elif 10 <= days_to_expiration < 20 or 40 < days_to_expiration <= 60:
                expiry_score = 7
            else:
                expiry_score = 3
            score += expiry_score
        
        # Store the score
        contract["score"] = score
    
    # Sort by score (descending)
    ranked_contracts = sorted(contracts, key=lambda x: x.get("score", 0), reverse=True)
    return ranked_contracts

def select_contract_for_signal(
    symbol: str,
    direction: str,
    max_price: float = 5.0,
    option_type: str = None
) -> Optional[Dict[str, Any]]:
    """Select the optimal contract for a given signal and direction."""
    # Get all options contracts for this symbol
    contracts = OptionsContractModel.query.filter_by(underlying=symbol).all()
    
    if not contracts:
        logger.warning(f"No options contracts found for {symbol}")
        return None
    
    # Convert to dictionary format
    contract_dicts = []
    for contract in contracts:
        contract_dict = {
            "symbol": contract.symbol,
            "underlying": contract.underlying,
            "expiration_date": contract.expiration_date,
            "strike": contract.strike,
            "option_type": contract.option_type,
            "bid": contract.bid,
            "ask": contract.ask,
            "last": contract.last,
            "volume": contract.volume,
            "open_interest": contract.open_interest,
            "implied_volatility": contract.implied_volatility,
            "delta": contract.delta,
            "gamma": contract.gamma,
            "theta": contract.theta,
            "vega": contract.vega,
            "rho": contract.rho
        }
        contract_dicts.append(contract_dict)
    
    # Create and apply filter chain
    filter_chain = create_directional_filter_chain(direction, option_type)
    filtered_contracts = filter_chain.apply_filters(contract_dicts)
    
    # Apply price filter separately
    price_filter = PriceFilter(min_price=0.1, max_price=max_price)
    filtered_contracts = price_filter.filter(filtered_contracts)
    
    if not filtered_contracts:
        logger.warning(f"No suitable options contracts found for {symbol} {direction}")
        return None
    
    # Rank contracts by desirability
    ranked_contracts = rank_contracts(filtered_contracts, direction)
    
    # Return the top-ranked contract
    return ranked_contracts[0] if ranked_contracts else None

def recommend_option_for_signal(signal_id: str, direction: str) -> Dict[str, Any]:
    """Recommend an options contract for a given signal ID."""
    from common.db_models import SignalModel, TickerSetupModel
    
    # Get the signal from the database
    signal = SignalModel.query.get(signal_id)
    if not signal:
        return {
            "status": "error",
            "message": f"Signal ID {signal_id} not found"
        }
    
    # Get the ticker setup
    ticker_setup = TickerSetupModel.query.get(signal.ticker_setup_id)
    if not ticker_setup:
        return {
            "status": "error",
            "message": f"Ticker setup not found for signal ID {signal_id}"
        }
    
    # Get the symbol
    symbol = ticker_setup.symbol
    
    # Select the optimal contract
    contract = select_contract_for_signal(symbol, direction)
    
    if not contract:
        return {
            "status": "error",
            "message": f"No suitable options contract found for {symbol} {direction}"
        }
    
    # Add signal information to the response
    response = {
        "status": "success",
        "signal": {
            "id": signal.id,
            "symbol": symbol,
            "category": signal.category,
            "comparison": signal.comparison,
            "trigger_value": json.loads(signal.trigger_value) if isinstance(signal.trigger_value, str) else signal.trigger_value
        },
        "recommendation": contract
    }
    
    return response

# Register routes for options selection
def register_contract_filter_routes(app):
    from flask import Blueprint, jsonify, request
    
    contract_filter_routes = Blueprint('contract_filter_routes', __name__)
    
    @contract_filter_routes.route('/api/options/filter/<symbol>', methods=['GET'])
    def filter_contracts_api(symbol):
        """Filter options contracts for a symbol."""
        direction = request.args.get('direction', 'bullish')
        option_type = request.args.get('type')
        max_price = request.args.get('max_price', 5.0, type=float)
        
        # Get all contracts for the symbol
        contracts = OptionsContractModel.query.filter_by(underlying=symbol).all()
        
        if not contracts:
            return jsonify({
                "status": "error",
                "message": f"No options contracts found for {symbol}"
            }), 404
        
        # Convert to dictionary format
        contract_dicts = []
        for contract in contracts:
            contract_dict = {
                "symbol": contract.symbol,
                "underlying": contract.underlying,
                "expiration_date": contract.expiration_date,
                "strike": contract.strike,
                "option_type": contract.option_type,
                "bid": contract.bid,
                "ask": contract.ask,
                "last": contract.last,
                "volume": contract.volume,
                "open_interest": contract.open_interest,
                "implied_volatility": contract.implied_volatility,
                "delta": contract.delta,
                "gamma": contract.gamma,
                "theta": contract.theta,
                "vega": contract.vega,
                "rho": contract.rho
            }
            contract_dicts.append(contract_dict)
        
        # Create and apply filter chain
        filter_chain = create_directional_filter_chain(direction, option_type)
        filtered_contracts = filter_chain.apply_filters(contract_dicts)
        
        # Apply price filter separately
        price_filter = PriceFilter(min_price=0.1, max_price=max_price)
        filtered_contracts = price_filter.filter(filtered_contracts)
        
        # Rank contracts
        ranked_contracts = rank_contracts(filtered_contracts, direction)
        
        return jsonify({
            "status": "success",
            "contracts": ranked_contracts,
            "original_count": len(contract_dicts),
            "filtered_count": len(ranked_contracts)
        })
    
    @contract_filter_routes.route('/api/options/recommend', methods=['POST'])
    def recommend_option_api():
        """Recommend an options contract for a given signal."""
        data = request.json
        signal_id = data.get('signal_id')
        direction = data.get('direction', 'bullish')
        
        if not signal_id:
            return jsonify({
                "status": "error",
                "message": "Signal ID is required"
            }), 400
        
        recommendation = recommend_option_for_signal(signal_id, direction)
        
        if recommendation.get("status") == "error":
            return jsonify(recommendation), 404
        
        return jsonify(recommendation)
    
    @contract_filter_routes.route('/api/options/recommend/<symbol>', methods=['GET'])
    def recommend_option_for_symbol_api(symbol):
        """Recommend an options contract for a given symbol and direction."""
        direction = request.args.get('direction', 'bullish')
        signal_id = request.args.get('signal_id')
        max_price = request.args.get('max_price', 5.0, type=float)
        
        if signal_id:
            # If signal ID is provided, delegate to the signal-based recommender
            recommendation = recommend_option_for_signal(signal_id, direction)
        else:
            # Otherwise, just use the symbol directly
            contract = select_contract_for_signal(symbol, direction, max_price)
            
            if not contract:
                recommendation = {
                    "status": "error",
                    "message": f"No suitable options contract found for {symbol} {direction}"
                }
            else:
                recommendation = {
                    "status": "success",
                    "recommendation": contract
                }
        
        if recommendation.get("status") == "error":
            return jsonify(recommendation), 404
        
        return jsonify(recommendation)
    
    # Register blueprint with app
    app.register_blueprint(contract_filter_routes)
    
    return contract_filter_routes