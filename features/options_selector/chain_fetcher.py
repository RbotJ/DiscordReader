import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple
import alpaca_trade_api as tradeapi
from common.models import OptionsContract
from common.utils import load_config

# Configure logging
logger = logging.getLogger(__name__)

# Cache for options chains to limit API calls
_options_chain_cache: Dict[str, Tuple[List[OptionsContract], datetime.datetime]] = {}
_cache_expiry_seconds = 300  # 5 minutes

def get_options_chain(symbol: str, expiry_date: Optional[str] = None) -> List[OptionsContract]:
    """
    Fetch options chain for a given symbol and expiry date
    
    Args:
        symbol: Ticker symbol (e.g., 'AAPL')
        expiry_date: Optional expiry date in ISO format (YYYY-MM-DD)
                     If not provided, fetches the nearest expiry date
    
    Returns:
        List of OptionsContract objects
    """
    # Check cache first
    cache_key = f"{symbol}:{expiry_date}"
    if cache_key in _options_chain_cache:
        contracts, timestamp = _options_chain_cache[cache_key]
        age = (datetime.datetime.now() - timestamp).total_seconds()
        if age < _cache_expiry_seconds:
            logger.debug(f"Using cached options chain for {cache_key} (age: {age:.1f}s)")
            return contracts
    
    # Load config
    config = load_config()
    
    try:
        # Initialize Alpaca API
        api = tradeapi.REST(
            key_id=config['alpaca']['api_key'],
            secret_key=config['alpaca']['api_secret'],
            base_url=config['alpaca']['base_url'],
            api_version='v2'
        )
        
        # If no expiry date provided, find the nearest one
        if not expiry_date:
            # Get available expiry dates
            expiry_dates = _get_expiry_dates(api, symbol)
            if not expiry_dates:
                logger.error(f"No expiry dates available for {symbol}")
                return []
            
            # Get the date closest to default_option_days from config
            default_days = config['settings']['default_option_days']
            target_date = datetime.date.today() + datetime.timedelta(days=default_days)
            
            # Find closest date
            closest_date = min(expiry_dates, key=lambda d: abs((d - target_date).days))
            expiry_date = closest_date.isoformat()
            logger.info(f"Selected expiry date {expiry_date} for {symbol}")
        
        # Convert string date to datetime if needed
        if isinstance(expiry_date, str):
            expiry_date = datetime.date.fromisoformat(expiry_date)
        
        # Format date for Alpaca API
        expiry_str = expiry_date.strftime("%Y-%m-%d")
        
        # Fetch options contracts for the expiry date
        logger.info(f"Fetching options chain for {symbol} expiring {expiry_str}")
        
        # First try Alpaca API
        try:
            # Get options data from Alpaca
            options_data = api.get_options_chain(symbol, expiry_str)
            contracts = _parse_alpaca_options(options_data)
        except Exception as e:
            logger.warning(f"Failed to get options from Alpaca: {str(e)}, using fallback method")
            # Fallback method - simulate basic options chain
            # This is just for development when Alpaca options API is not available
            contracts = _generate_mock_options_chain(symbol, expiry_date)
        
        # Cache the result
        _options_chain_cache[cache_key] = (contracts, datetime.datetime.now())
        
        return contracts
    
    except Exception as e:
        logger.error(f"Error fetching options chain: {str(e)}")
        return []

def _get_expiry_dates(api, symbol: str) -> List[datetime.date]:
    """Get available expiry dates for a symbol"""
    try:
        # Try to fetch from Alpaca
        expiry_dates = api.get_options_expirations(symbol)
        
        # Convert to datetime.date objects
        return [datetime.date.fromisoformat(d) for d in expiry_dates]
    except Exception as e:
        logger.warning(f"Failed to get expiry dates: {str(e)}, using fallback method")
        
        # Fallback method - generate some standard expiry dates
        # This is just for development when Alpaca options API is not available
        today = datetime.date.today()
        
        # Generate weekly expirations for next 8 weeks (approximate)
        weekly = []
        for i in range(1, 9):
            # Find the Friday of each week
            days_until_friday = (4 - today.weekday()) % 7
            if i > 1:
                days_until_friday += (i-1) * 7
            friday = today + datetime.timedelta(days=days_until_friday)
            weekly.append(friday)
        
        # Generate monthly expirations for next 6 months
        monthly = []
        for i in range(1, 7):
            # Find the third Friday of each month
            next_month = today.replace(month=((today.month + i - 1) % 12) + 1)
            if today.month + i > 12:
                next_month = next_month.replace(year=today.year + 1)
            
            # Find first day of month
            first_day = next_month.replace(day=1)
            
            # Find first Friday
            days_until_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + datetime.timedelta(days=days_until_friday)
            
            # Third Friday is 2 weeks after first Friday
            third_friday = first_friday + datetime.timedelta(days=14)
            monthly.append(third_friday)
        
        return weekly + monthly

def _parse_alpaca_options(options_data: List[Dict[str, Any]]) -> List[OptionsContract]:
    """Parse options data from Alpaca API"""
    contracts = []
    
    for contract_data in options_data:
        try:
            # Extract contract details
            symbol = contract_data["symbol"]
            underlying = contract_data["underlying_symbol"]
            expiration = datetime.date.fromisoformat(contract_data["expiration_date"])
            strike = float(contract_data["strike_price"])
            option_type = contract_data["side"].lower()  # 'call' or 'put'
            
            # Extract pricing and Greeks
            bid = float(contract_data.get("bid_price", 0))
            ask = float(contract_data.get("ask_price", 0))
            last = float(contract_data.get("last_price", 0))
            volume = int(contract_data.get("volume", 0))
            open_interest = int(contract_data.get("open_interest", 0))
            
            # Create contract object
            contract = OptionsContract(
                symbol=symbol,
                underlying=underlying,
                strike=strike,
                expiration=expiration,
                option_type=option_type,
                bid=bid,
                ask=ask,
                last=last,
                volume=volume,
                open_interest=open_interest,
                implied_volatility=float(contract_data.get("implied_volatility", 0)),
                delta=float(contract_data.get("delta", 0)),
                gamma=float(contract_data.get("gamma", 0)),
                theta=float(contract_data.get("theta", 0)),
                vega=float(contract_data.get("vega", 0)),
                rho=float(contract_data.get("rho", 0))
            )
            
            contracts.append(contract)
        except Exception as e:
            logger.error(f"Error parsing option contract: {str(e)}")
    
    return contracts

def _generate_mock_options_chain(symbol: str, expiry_date: datetime.date) -> List[OptionsContract]:
    """
    Generate a mock options chain for development/testing
    
    This is used only when the Alpaca options API is not available
    """
    from features.market.price_feed import get_last_price
    
    logger.warning(f"Generating mock options chain for {symbol} - FOR DEVELOPMENT ONLY")
    
    contracts = []
    
    # Get current price
    current_price = get_last_price(symbol)
    if current_price <= 0:
        # Fallback price if real price not available
        current_price = 100.0
    
    # Generate strikes around current price
    strikes = []
    price_step = max(1.0, round(current_price * 0.025, 1))  # 2.5% steps, min $1
    
    for i in range(-10, 11):
        strike = round(current_price + (i * price_step), 1)
        if strike > 0:
            strikes.append(strike)
    
    # Calculate days to expiration
    days_to_expiry = (expiry_date - datetime.date.today()).days
    
    # Base implied volatility - higher for longer dates
    base_iv = 0.3 + (days_to_expiry / 365) * 0.1
    
    # Generate contracts for each strike
    for strike in strikes:
        # Calls
        call_symbol = f"{symbol}{expiry_date.strftime('%y%m%d')}C{int(strike*100):08d}"
        
        # Simple option pricing model
        call_intrinsic = max(0, current_price - strike)
        call_time_value = current_price * base_iv * (days_to_expiry / 365) * 0.4
        call_price = call_intrinsic + call_time_value
        
        # Simple Greeks calculations
        call_delta = max(0, min(1, 0.5 + ((current_price - strike) / (current_price * 0.2))))
        call_gamma = max(0, 0.08 - abs(strike - current_price) / current_price)
        call_theta = -call_time_value / max(1, days_to_expiry)
        call_vega = current_price * 0.01 * (days_to_expiry / 365)
        call_rho = max(0, call_delta) * (days_to_expiry / 365)
        
        # Create call contract
        call_contract = OptionsContract(
            symbol=call_symbol,
            underlying=symbol,
            strike=strike,
            expiration=expiry_date,
            option_type="call",
            bid=round(call_price * 0.95, 2),
            ask=round(call_price * 1.05, 2),
            last=round(call_price, 2),
            volume=int(100 * (1 - abs(strike - current_price) / current_price)),
            open_interest=int(500 * (1 - abs(strike - current_price) / current_price)),
            implied_volatility=base_iv,
            delta=call_delta,
            gamma=call_gamma,
            theta=call_theta,
            vega=call_vega,
            rho=call_rho
        )
        contracts.append(call_contract)
        
        # Puts
        put_symbol = f"{symbol}{expiry_date.strftime('%y%m%d')}P{int(strike*100):08d}"
        
        # Simple option pricing model
        put_intrinsic = max(0, strike - current_price)
        put_time_value = current_price * base_iv * (days_to_expiry / 365) * 0.4
        put_price = put_intrinsic + put_time_value
        
        # Simple Greeks calculations
        put_delta = min(0, max(-1, -0.5 + ((current_price - strike) / (current_price * 0.2))))
        put_gamma = max(0, 0.08 - abs(strike - current_price) / current_price)
        put_theta = -put_time_value / max(1, days_to_expiry)
        put_vega = current_price * 0.01 * (days_to_expiry / 365)
        put_rho = min(0, put_delta) * (days_to_expiry / 365)
        
        # Create put contract
        put_contract = OptionsContract(
            symbol=put_symbol,
            underlying=symbol,
            strike=strike,
            expiration=expiry_date,
            option_type="put",
            bid=round(put_price * 0.95, 2),
            ask=round(put_price * 1.05, 2),
            last=round(put_price, 2),
            volume=int(100 * (1 - abs(strike - current_price) / current_price)),
            open_interest=int(500 * (1 - abs(strike - current_price) / current_price)),
            implied_volatility=base_iv,
            delta=put_delta,
            gamma=put_gamma,
            theta=put_theta,
            vega=put_vega,
            rho=put_rho
        )
        contracts.append(put_contract)
    
    return contracts

def clear_cache() -> None:
    """Clear the options chain cache"""
    global _options_chain_cache
    _options_chain_cache = {}
    logger.info("Options chain cache cleared")
