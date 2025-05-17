"""
Alpaca Options Module

This module provides functionality for interacting with options data
through the Alpaca API, including fetching option chains and selecting
appropriate contracts based on trading strategies.
"""
from datetime import date, datetime, timedelta
import json
import logging
import os
from typing import Dict, List, Optional, Union

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.data.enums import OptionsFeed

# Define contract type enum (not available in the current Alpaca SDK version)
class ContractType:
    CALL = "call"
    PUT = "put"

from common.redis_utils import get_redis_client
from common.constants import OptionType

logger = logging.getLogger(__name__)

OPTIONS_CACHE_PREFIX = "options_chain_"
CACHE_TTL = 900  # 15 minutes

# Initialize API credentials from environment variables
API_KEY = os.environ.get("ALPACA_API_KEY")
API_SECRET = os.environ.get("ALPACA_API_SECRET")

options_historical_client = None
if API_KEY and API_SECRET:
    try:
        options_historical_client = OptionHistoricalDataClient(API_KEY, API_SECRET)
        logger.info("Alpaca options historical client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Alpaca options historical client: {e}")


class OptionsChainFetcher:
    """
    Class for fetching and managing options chain data from Alpaca.
    """
    def __init__(self, api_key: str = API_KEY, api_secret: str = API_SECRET):
        """
        Initialize the options chain fetcher.
        
        Args:
            api_key: Alpaca API key (default: from environment)
            api_secret: Alpaca API secret (default: from environment)
        """
        if not api_key or not api_secret:
            raise ValueError("Alpaca API credentials required")
            
        self.client = options_historical_client or OptionHistoricalDataClient(api_key, api_secret)
        self.redis = get_redis_client()

    def get_chain(
        self,
        symbol: str,
        expiration: Union[str, date] = None,
        strike_price: float = None,
        option_type: Union[str, OptionType] = None,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """
        Get options chain for a symbol with optional filters.
        
        Args:
            symbol: Underlying ticker symbol
            expiration: Expiration date (string or date object)
            strike_price: Strike price filter (exact match)
            option_type: "call", "put", or None for both
            force_refresh: Force fresh data from API instead of cache
            
        Returns:
            List of option contract dictionaries
        """
        # Create cache key
        cache_key = (
            f"{OPTIONS_CACHE_PREFIX}{symbol}_"
            f"{expiration or 'all'}_"
            f"{strike_price or 'all'}_"
            f"{option_type or 'all'}"
        )
        
        # Try to get from cache if not forcing refresh
        if not force_refresh and self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except Exception as e:
                    logger.error(f"Cache parse error: {e}")

        # Parse option_type to ContractType
        contract_type = None
        if option_type:
            if isinstance(option_type, OptionType):
                option_type = option_type.value
                
            if option_type.lower() == "call":
                contract_type = ContractType.CALL
            elif option_type.lower() == "put":
                contract_type = ContractType.PUT

        # Build the request
        # Try OPRA first, but fall back to INDICATIVE if OPRA access isn't available
        try_opra_first = True
        
        if try_opra_first:
            req = OptionChainRequest(
                underlying_symbol=symbol,
                expiration_date=expiration,
                strike_price_gte=strike_price,
                strike_price_lte=strike_price,
                type=contract_type,
                feed=OptionsFeed.OPRA
            )

        # Fetch and format
        try:
            raw_chain = self.client.get_option_chain(req)
            formatted = self._format_options_chain(raw_chain)
            
            # Cache the result
            if self.redis:
                self.redis.set(cache_key, json.dumps(formatted), ex=CACHE_TTL)
                
            return formatted

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching options chain for {symbol}: {error_msg}")
            
            # Check if it's the OPRA agreement error and try with INDICATIVE feed
            if "OPRA agreement is not signed" in error_msg and try_opra_first:
                logger.info(f"Falling back to INDICATIVE feed for {symbol}")
                try:
                    req = OptionChainRequest(
                        underlying_symbol=symbol,
                        expiration_date=expiration,
                        strike_price_gte=strike_price,
                        strike_price_lte=strike_price,
                        type=contract_type,
                        feed=OptionsFeed.INDICATIVE
                    )
                    
                    raw_chain = self.client.get_option_chain(req)
                    formatted = self._format_options_chain(raw_chain)
                    
                    # Cache the result
                    if self.redis:
                        self.redis.set(cache_key, json.dumps(formatted), ex=CACHE_TTL)
                        
                    return formatted
                    
                except Exception as fallback_error:
                    logger.error(f"Error using INDICATIVE feed fallback: {fallback_error}")
            
            # If we reach here, both attempts failed or it was a different error
            return []

    def _format_options_chain(self, raw_chain: Dict) -> List[Dict]:
        """
        Format the raw options chain response.
        
        Args:
            raw_chain: Raw response from Alpaca API
            
        Returns:
            List of formatted option contracts
        """
        result = []
        
        try:
            # Process different possible response formats
            if hasattr(raw_chain, 'data') and isinstance(raw_chain.data, dict):
                contracts = raw_chain.data
            elif isinstance(raw_chain, dict) and 'data' in raw_chain:
                contracts = raw_chain['data']
            elif isinstance(raw_chain, dict):
                contracts = raw_chain
            else:
                logger.error(f"Unexpected format in options chain response: {type(raw_chain)}")
                return []
                
            # Process each contract
            for symbol, contract_data in contracts.items():
                contract = {
                    'symbol': symbol,
                    'underlying_symbol': contract_data.get('underlying_symbol', ''),
                    'strike_price': float(contract_data.get('strike_price', 0)),
                    'expiration': contract_data.get('expiration_date', ''),
                    'option_type': 'call' if contract_data.get('type') == 'call' else 'put',
                    'bid': float(contract_data.get('bid_price', 0) or 0),
                    'ask': float(contract_data.get('ask_price', 0) or 0),
                    'last': float(contract_data.get('last_price', 0) or 0),
                    'volume': int(contract_data.get('volume', 0) or 0),
                    'open_interest': int(contract_data.get('open_interest', 0) or 0),
                    'iv': float(contract_data.get('implied_volatility', 0) or 0),
                    'delta': float(contract_data.get('delta', 0) or 0),
                    'gamma': float(contract_data.get('gamma', 0) or 0),
                    'theta': float(contract_data.get('theta', 0) or 0),
                    'vega': float(contract_data.get('vega', 0) or 0),
                    'updated_at': contract_data.get('updated_at', ''),
                }
                result.append(contract)
                
        except Exception as e:
            logger.error(f"Error formatting options chain: {e}")
            
        return result

    def get_same_day_expiration(self, symbol: str) -> Optional[date]:
        """
        Get the same-day expiration date if available, otherwise the next available.
        
        Args:
            symbol: Underlying ticker symbol
            
        Returns:
            The expiration date or None if not found
        """
        today = date.today()
        
        try:
            # Try OPRA first, then fall back to INDICATIVE if needed
            try:
                req = OptionChainRequest(
                    underlying_symbol=symbol,
                    feed=OptionsFeed.OPRA,
                )
                raw_chain = self.client.get_option_chain(req)
            except Exception as e:
                error_msg = str(e)
                if "OPRA agreement is not signed" in error_msg:
                    logger.info(f"Falling back to INDICATIVE feed for expirations of {symbol}")
                    req = OptionChainRequest(
                        underlying_symbol=symbol,
                        feed=OptionsFeed.INDICATIVE,
                    )
                    raw_chain = self.client.get_option_chain(req)
                else:
                    # Re-raise if it's not the OPRA error
                    raise
            
            # Extract unique expiration dates
            expirations = set()
            if isinstance(raw_chain, dict):
                for contract in raw_chain.values():
                    if 'expiration_date' in contract:
                        exp_date = contract['expiration_date']
                        if isinstance(exp_date, str):
                            exp_date = datetime.strptime(exp_date, '%Y-%m-%d').date()
                        expirations.add(exp_date)
            
            # Sort expirations
            sorted_expirations = sorted(expirations)
            
            # Find same-day or next available
            for exp in sorted_expirations:
                if exp >= today:
                    return exp
                    
            return None
            
        except Exception as e:
            logger.error(f"Error finding same-day expiration for {symbol}: {e}")
            return None

    def find_atm_options(
        self, 
        symbol: str, 
        option_type: Union[str, OptionType], 
        target_delta: float = 0.50,
        expiration: Union[str, date] = None
    ) -> Optional[Dict]:
        """
        Find at-the-money options for a symbol.
        
        Args:
            symbol: Underlying ticker symbol
            option_type: "call" or "put"
            target_delta: Target delta value (default: 0.50 for ATM)
            expiration: Optional specific expiration date
            
        Returns:
            Best matching option contract or None if not found
        """
        if expiration is None:
            # Try to find same-day expiration
            expiration = self.get_same_day_expiration(symbol)
            if not expiration:
                logger.error(f"Could not find suitable expiration for {symbol}")
                return None
        
        # Try with fallback to INDICATIVE feed if needed
        try:
            chain = self.get_chain(
                symbol=symbol,
                expiration=expiration,
                option_type=option_type
            )
        except Exception as e:
            error_msg = str(e)
            if "OPRA agreement is not signed" in error_msg:
                logger.info(f"Falling back to INDICATIVE feed for ATM options on {symbol}")
                req = OptionChainRequest(
                    underlying_symbol=symbol,
                    expiration_date=expiration,
                    type=ContractType.CALL if option_type == "call" else ContractType.PUT,
                    feed=OptionsFeed.INDICATIVE
                )
                
                try:
                    raw_chain = self.client.get_option_chain(req)
                    chain = self._format_options_chain(raw_chain)
                except Exception as fallback_error:
                    logger.error(f"Error with INDICATIVE feed fallback for ATM options: {fallback_error}")
                    chain = []
            else:
                logger.error(f"Error finding ATM options: {e}")
                chain = []
        
        if not chain:
            logger.error(f"No options found for {symbol} exp:{expiration} type:{option_type}")
            return None
            
        # Find closest to target delta
        best_match = None
        closest_delta_diff = float('inf')
        
        for contract in chain:
            delta = abs(contract.get('delta', 0) or 0)
            delta_diff = abs(delta - target_delta)
            
            if delta_diff < closest_delta_diff:
                closest_delta_diff = delta_diff
                best_match = contract
                
        return best_match


def get_options_fetcher() -> Optional[OptionsChainFetcher]:
    """
    Get an options chain fetcher instance.
    
    Returns:
        OptionsChainFetcher instance or None if not available
    """
    if not API_KEY or not API_SECRET:
        logger.error("Alpaca API credentials not set in environment")
        return None
        
    try:
        return OptionsChainFetcher(API_KEY, API_SECRET)
    except Exception as e:
        logger.error(f"Error creating options fetcher: {e}")
        return None