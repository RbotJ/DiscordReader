import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import math

from common.models import OptionsContract
from common.utils import load_config
from features.market.price_feed import get_last_price
from .chain_fetcher import get_options_chain
from .greeks_calculator import update_contract_greeks

# Configure logging
logger = logging.getLogger(__name__)

def select_optimal_contracts(
    symbol: str,
    direction: str,
    price_target: Optional[float] = None,
    max_contracts: int = 3
) -> List[OptionsContract]:
    """
    Select optimal option contracts based on direction and criteria
    
    Args:
        symbol: Underlying symbol
        direction: 'bullish' or 'bearish'
        price_target: Optional price target (used to optimize selection)
        max_contracts: Maximum number of contracts to return
        
    Returns:
        List of selected OptionsContract objects
    """
    try:
        # Get configuration
        config = load_config()
        target_delta = config['settings']['target_delta']
        
        # Get current price
        current_price = get_last_price(symbol)
        if current_price <= 0:
            logger.error(f"Failed to get current price for {symbol}")
            return []
        
        # Get options chain
        all_contracts = get_options_chain(symbol)
        if not all_contracts:
            logger.error(f"No options available for {symbol}")
            return []
        
        # Calculate percentage move to target if provided
        target_percent = None
        if price_target:
            target_percent = (price_target - current_price) / current_price
        
        # Filter by option type based on direction
        option_type = "call" if direction.lower() == "bullish" else "put"
        filtered_contracts = [c for c in all_contracts if c.option_type == option_type]
        
        # Update Greeks for each contract
        for contract in filtered_contracts:
            update_contract_greeks(contract, current_price)
        
        # Apply filters
        filtered_contracts = _apply_filters(filtered_contracts, current_price)
        
        # Score contracts
        scored_contracts = _score_contracts(
            filtered_contracts, 
            current_price, 
            target_delta,
            target_percent
        )
        
        # Sort by score (descending)
        scored_contracts.sort(key=lambda x: x[1], reverse=True)
        
        # Return top contracts
        return [contract for contract, score in scored_contracts[:max_contracts]]
        
    except Exception as e:
        logger.error(f"Error selecting optimal contracts: {str(e)}")
        return []

def _apply_filters(contracts: List[OptionsContract], current_price: float) -> List[OptionsContract]:
    """Apply basic filters to remove illiquid or extreme contracts"""
    filtered = []
    
    for contract in contracts:
        # Skip contracts with zero or very low liquidity
        if contract.volume < 10 and contract.open_interest < 50:
            continue
        
        # Skip deep ITM or OTM contracts
        if contract.option_type == "call":
            moneyness = contract.strike / current_price
            if moneyness < 0.7 or moneyness > 1.3:
                continue
        else:  # put
            moneyness = current_price / contract.strike
            if moneyness < 0.7 or moneyness > 1.3:
                continue
        
        # Skip very cheap options (likely worthless)
        if (contract.bid + contract.ask) / 2 < 0.1:
            continue
        
        # Skip options with extreme implied volatility
        if contract.implied_volatility > 2.0:
            continue
        
        filtered.append(contract)
    
    return filtered

def _score_contracts(
    contracts: List[OptionsContract], 
    current_price: float,
    target_delta: float,
    target_percent: Optional[float] = None
) -> List[tuple]:
    """Score contracts based on multiple criteria"""
    scored_contracts = []
    
    for contract in contracts:
        # Initialize score
        score = 0.0
        
        # 1. Delta score - prioritize contracts with delta close to target
        delta_score = 1.0 - min(1.0, abs(abs(contract.delta) - target_delta) / target_delta)
        score += delta_score * 30  # Weight: 30%
        
        # 2. Liquidity score - based on volume and open interest
        liquidity_score = min(1.0, math.log10(max(10, contract.volume + contract.open_interest / 2)) / 3)
        score += liquidity_score * 20  # Weight: 20%
        
        # 3. Bid-ask spread score - tighter spreads are better
        mid_price = (contract.bid + contract.ask) / 2
        if mid_price > 0:
            spread_percent = (contract.ask - contract.bid) / mid_price
            spread_score = max(0.0, 1.0 - spread_percent * 5)  # Penalize spreads > 20%
        else:
            spread_score = 0.0
        score += spread_score * 15  # Weight: 15%
        
        # 4. Days to expiry score - favor options with enough time
        days_to_expiry = (contract.expiration - date.today()).days
        time_score = min(1.0, days_to_expiry / 60)  # Scale up to 60 days
        score += time_score * 15  # Weight: 15%
        
        # 5. Strike proximity score - favor strikes aligned with directional view
        if target_percent:
            # Calculate ideal strike based on target
            ideal_strike = current_price * (1 + target_percent)
            
            # Score based on distance from ideal strike
            strike_distance = abs(contract.strike - ideal_strike) / current_price
            strike_score = max(0.0, 1.0 - strike_distance)
            score += strike_score * 20  # Weight: 20%
        else:
            # Without a target, favor slightly OTM options
            if contract.option_type == "call":
                moneyness = contract.strike / current_price
                strike_score = 1.0 - min(1.0, abs(moneyness - 1.05) / 0.15)
            else:  # put
                moneyness = current_price / contract.strike
                strike_score = 1.0 - min(1.0, abs(moneyness - 1.05) / 0.15)
            
            score += strike_score * 20  # Weight: 20%
        
        scored_contracts.append((contract, score))
    
    return scored_contracts

def filter_by_criteria(
    contracts: List[OptionsContract],
    min_delta: Optional[float] = None,
    max_delta: Optional[float] = None,
    min_days: Optional[int] = None,
    max_days: Optional[int] = None,
    min_volume: Optional[int] = None,
    min_open_interest: Optional[int] = None
) -> List[OptionsContract]:
    """
    Filter contracts by specific criteria
    
    Args:
        contracts: List of OptionsContract objects
        min_delta: Minimum absolute delta value
        max_delta: Maximum absolute delta value
        min_days: Minimum days to expiration
        max_days: Maximum days to expiration
        min_volume: Minimum volume
        min_open_interest: Minimum open interest
    
    Returns:
        Filtered list of OptionsContract objects
    """
    filtered = []
    today = date.today()
    
    for contract in contracts:
        # Delta filter
        if min_delta is not None and abs(contract.delta) < min_delta:
            continue
        if max_delta is not None and abs(contract.delta) > max_delta:
            continue
        
        # Days to expiry filter
        days_to_expiry = (contract.expiration - today).days
        if min_days is not None and days_to_expiry < min_days:
            continue
        if max_days is not None and days_to_expiry > max_days:
            continue
        
        # Volume filter
        if min_volume is not None and contract.volume < min_volume:
            continue
        
        # Open interest filter
        if min_open_interest is not None and contract.open_interest < min_open_interest:
            continue
        
        filtered.append(contract)
    
    return filtered
