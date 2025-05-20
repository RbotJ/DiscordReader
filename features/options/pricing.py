"""
Options Pricing Module

This module provides functionality for fetching and analyzing options pricing data
from Alpaca's API, with a focus on near-the-money ODTE (0 Days To Expiration) contracts.
"""
import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, date, timedelta

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, OptionSnapshotRequest
from alpaca.data.enums import OptionSide

# Configure logger
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET')

class OptionsPricingService:
    """
    Service for fetching and analyzing options pricing data.
    """
    
    def __init__(self):
        """Initialize the options pricing service."""
        self.client = None
        self.initialized = False
        self.chain_cache = {}  # Cache for option chains
        
        # Initialize client
        self._initialize_client()
        
    def _initialize_client(self) -> bool:
        """
        Initialize the Alpaca options data client.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not ALPACA_API_KEY or not ALPACA_API_SECRET:
            logger.warning("Alpaca API credentials not found in environment variables")
            return False
            
        try:
            self.client = OptionHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
            self.initialized = True
            logger.info("Options data client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing options data client: {e}")
            return False
            
    def get_option_chain(
        self, 
        symbol: str,
        expiration_date: Optional[Union[str, date]] = None
    ) -> Optional[Dict]:
        """
        Get the option chain for a symbol and expiration date.
        
        Args:
            symbol: Underlying ticker symbol
            expiration_date: Expiration date (optional, defaults to nearest expiration)
            
        Returns:
            Dict containing option chain data or None on error
        """
        if not self.initialized or not self.client:
            logger.warning("Options data client not initialized")
            return None
            
        try:
            # If no expiration date specified, get the nearest expiration
            if expiration_date is None:
                expiration_dates = self.get_expiration_dates(symbol)
                if not expiration_dates:
                    logger.warning(f"No expiration dates found for {symbol}")
                    return None
                    
                expiration_date = expiration_dates[0]  # Nearest expiration
                
            # Handle string dates
            if isinstance(expiration_date, str):
                try:
                    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid expiration date format: {expiration_date}")
                    return None
                    
            # Check cache
            cache_key = f"{symbol}_{expiration_date}"
            if cache_key in self.chain_cache:
                return self.chain_cache[cache_key]
            
            # Create request
            request = OptionChainRequest(
                symbol_or_symbols=symbol,
                expiration_date=expiration_date
            )
            
            # Get chain
            chain = self.client.get_option_chain(request_params=request)
            
            # Process and cache result
            result = {
                "symbol": symbol,
                "expiration_date": expiration_date.isoformat(),
                "calls": [],
                "puts": []
            }
            
            for contract in chain:
                # Convert to dict for easier handling
                contract_dict = {
                    "symbol": contract.symbol,
                    "underlying_symbol": symbol,
                    "expiration_date": contract.expiration_date.isoformat(),
                    "strike_price": float(contract.strike_price),
                    "side": "call" if contract.contract_type == OptionSide.CALL else "put"
                }
                
                # Add to appropriate list
                if contract.contract_type == OptionSide.CALL:
                    result["calls"].append(contract_dict)
                else:
                    result["puts"].append(contract_dict)
                    
            # Sort by strike price
            result["calls"].sort(key=lambda x: x["strike_price"])
            result["puts"].sort(key=lambda x: x["strike_price"])
            
            # Cache result
            self.chain_cache[cache_key] = result
            
            return result
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}")
            return None
            
    def get_expiration_dates(self, symbol: str) -> List[date]:
        """
        Get available expiration dates for a symbol.
        
        Args:
            symbol: Underlying ticker symbol
            
        Returns:
            List of expiration dates (sorted by nearest first)
        """
        if not self.initialized or not self.client:
            logger.warning("Options data client not initialized")
            return []
            
        try:
            # First try to get ODTE expirations (today)
            today = datetime.now().date()
            request = OptionChainRequest(
                symbol_or_symbols=symbol
            )
            
            # Get chain to extract expiration dates
            chain = self.client.get_option_chain(request_params=request)
            
            # Extract unique expiration dates
            dates = set()
            for contract in chain:
                dates.add(contract.expiration_date)
                
            # Sort dates (nearest first)
            sorted_dates = sorted(dates)
            
            return sorted_dates
        except Exception as e:
            logger.error(f"Error getting expiration dates for {symbol}: {e}")
            return []
            
    def get_nearest_expiration(self, symbol: str) -> Optional[date]:
        """
        Get the nearest expiration date for a symbol.
        
        Args:
            symbol: Underlying ticker symbol
            
        Returns:
            Nearest expiration date or None if not found
        """
        dates = self.get_expiration_dates(symbol)
        return dates[0] if dates else None
        
    def get_option_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get current quotes for multiple option symbols.
        
        Args:
            symbols: List of option symbols
            
        Returns:
            Dict mapping option symbols to quote data
        """
        if not self.initialized or not self.client:
            logger.warning("Options data client not initialized")
            return {}
            
        if not symbols:
            return {}
            
        try:
            # Create request
            request = OptionSnapshotRequest(
                symbol_or_symbols=symbols
            )
            
            # Get snapshots
            snapshots = self.client.get_option_snapshot(request_params=request)
            
            # Process results
            result = {}
            for symbol, snapshot in snapshots.items():
                quote_data = {
                    "symbol": symbol,
                    "ask": float(snapshot.ask_price) if snapshot.ask_price else None,
                    "bid": float(snapshot.bid_price) if snapshot.bid_price else None,
                    "last": float(snapshot.latest_trade.price) if snapshot.latest_trade else None,
                    "volume": int(snapshot.volume) if snapshot.volume else 0,
                    "open_interest": int(snapshot.open_interest) if snapshot.open_interest else 0,
                    "underlying_price": float(snapshot.underlying_price) if snapshot.underlying_price else None,
                    "implied_volatility": float(snapshot.implied_volatility) if snapshot.implied_volatility else None,
                    "delta": float(snapshot.delta) if snapshot.delta else None,
                    "gamma": float(snapshot.gamma) if snapshot.gamma else None,
                    "theta": float(snapshot.theta) if snapshot.theta else None,
                    "vega": float(snapshot.vega) if snapshot.vega else None
                }
                result[symbol] = quote_data
                
            return result
        except Exception as e:
            logger.error(f"Error getting option quotes: {e}")
            return {}
            
    def get_near_the_money_options(
        self, 
        symbol: str, 
        expiration_date: Optional[Union[str, date]] = None,
        num_strikes: int = 5,
        underlying_price: Optional[float] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get near-the-money options for a symbol.
        
        Args:
            symbol: Underlying ticker symbol
            expiration_date: Expiration date (optional, defaults to nearest expiration)
            num_strikes: Number of strikes above and below current price
            underlying_price: Current price of underlying (optional, will be fetched if not provided)
            
        Returns:
            Dict with 'calls' and 'puts' lists of near-the-money options
        """
        # Get option chain
        chain = self.get_option_chain(symbol, expiration_date)
        if not chain:
            return {"calls": [], "puts": []}
            
        # Get current price if not provided
        if underlying_price is None:
            from features.market.api import get_latest_price
            underlying_price = get_latest_price(symbol)
            
            if underlying_price is None:
                logger.warning(f"Could not get current price for {symbol}")
                return {"calls": [], "puts": []}
                
        # Find strikes near the current price
        all_strikes = set()
        for option in chain["calls"] + chain["puts"]:
            all_strikes.add(option["strike_price"])
            
        all_strikes = sorted(all_strikes)
        
        # Find closest strike to current price
        closest_idx = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - underlying_price))
        
        # Get strikes around the closest
        start_idx = max(0, closest_idx - num_strikes)
        end_idx = min(len(all_strikes) - 1, closest_idx + num_strikes)
        
        selected_strikes = all_strikes[start_idx:end_idx + 1]
        
        # Filter chains to only include selected strikes
        calls = [opt for opt in chain["calls"] if opt["strike_price"] in selected_strikes]
        puts = [opt for opt in chain["puts"] if opt["strike_price"] in selected_strikes]
        
        # Get quotes for selected options
        option_symbols = [opt["symbol"] for opt in calls + puts]
        quotes = self.get_option_quotes(option_symbols)
        
        # Add quote data to options
        for options_list in [calls, puts]:
            for option in options_list:
                symbol = option["symbol"]
                if symbol in quotes:
                    option.update(quotes[symbol])
                    
                    # Calculate distance from ATM as percentage
                    if underlying_price:
                        atm_distance_pct = abs(option["strike_price"] - underlying_price) / underlying_price * 100
                        option["atm_distance_pct"] = round(atm_distance_pct, 2)
        
        return {
            "calls": calls,
            "puts": puts,
            "underlying_price": underlying_price,
            "strikes": selected_strikes
        }
        
    def get_odte_options(self, symbol: str, num_strikes: int = 5) -> Dict[str, List[Dict]]:
        """
        Get 0 DTE (Days To Expiration) options for a symbol.
        
        Args:
            symbol: Underlying ticker symbol
            num_strikes: Number of strikes above and below current price
            
        Returns:
            Dict with 'calls' and 'puts' lists of 0 DTE options
        """
        # Get today's date
        today = datetime.now().date()
        
        # Get expiration dates
        expirations = self.get_expiration_dates(symbol)
        if not expirations:
            logger.warning(f"No expirations found for {symbol}")
            return {"calls": [], "puts": []}
            
        # Find today's expiration if it exists, otherwise get the nearest
        expiration = None
        for exp in expirations:
            if exp == today:
                expiration = exp
                break
                
        if not expiration:
            # If no ODTE, get the nearest expiration
            expiration = expirations[0]
            logger.info(f"No 0 DTE options for {symbol}, using nearest expiration: {expiration}")
            
        # Get near-the-money options for this expiration
        return self.get_near_the_money_options(symbol, expiration, num_strikes)
        
    def clear_cache(self):
        """Clear the chain cache."""
        self.chain_cache = {}
        logger.info("Option chain cache cleared")

# Global instance
options_pricing = OptionsPricingService()

def get_options_pricing() -> OptionsPricingService:
    """
    Get the global options pricing service instance.
    
    Returns:
        OptionsPricingService instance
    """
    return options_pricing