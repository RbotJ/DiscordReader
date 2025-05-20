"""
Options Contract Selector

This module provides functionality to select the most appropriate options contracts
for trading based on signals and market conditions.
"""
import logging
import datetime
from typing import Dict, List, Optional, Tuple, Union

from features.alpaca.client import get_option_data_client, get_stock_data_client
from features.alpaca.options_enums import OptionSide

# Configure logger
logger = logging.getLogger(__name__)

def find_atm_options(
    symbol: str,
    expiration_days: int = 0,
    option_side: str = "call",
    price_buffer_percent: float = 0.02
) -> List[Dict]:
    """
    Find at-the-money options for a given symbol.
    
    Args:
        symbol: The underlying ticker symbol
        expiration_days: Days until expiration (0 for same-day expiry)
        option_side: "call" or "put"
        price_buffer_percent: Percentage buffer around current price to consider ATM
        
    Returns:
        List of option contract dictionaries
    """
    try:
        # Get current price
        stock_client = get_stock_data_client()
        if not stock_client:
            logger.error("Stock data client not initialized")
            return []
            
        # Get latest quote
        quote_response = stock_client.get_stock_latest_quote(symbol_or_symbols=symbol)
        if not quote_response or symbol not in quote_response:
            logger.error(f"Could not get latest quote for {symbol}")
            return []
            
        quote = quote_response[symbol]
        
        # Calculate mid price
        if not hasattr(quote, 'ask_price') or not hasattr(quote, 'bid_price'):
            logger.error(f"Invalid quote for {symbol}")
            return []
            
        current_price = (quote.ask_price + quote.bid_price) / 2
        
        # Calculate price range
        price_buffer = current_price * price_buffer_percent
        min_strike = current_price - price_buffer
        max_strike = current_price + price_buffer
        
        # Get option client
        option_client = get_option_data_client()
        if not option_client:
            logger.error("Option data client not initialized")
            return []
            
        # Calculate expiration date
        today = datetime.date.today()
        expiration_date = today + datetime.timedelta(days=expiration_days)
        
        # Format the date for Alpaca API
        expiration_str = expiration_date.strftime("%Y-%m-%d")
        
        # Convert option_side to OptionSide enum
        side = OptionSide.CALL if option_side.lower() == "call" else OptionSide.PUT
        
        # Get options chain
        try:
            options_chain = option_client.get_option_chain(
                symbol_or_symbols=symbol,
                expiration_date=expiration_str
            )
            
            if not options_chain:
                logger.error(f"No options chain found for {symbol} with expiration {expiration_str}")
                return []
                
            # Filter for at-the-money options
            atm_options = []
            
            for contract in options_chain:
                if not hasattr(contract, 'strike_price') or not hasattr(contract, 'side'):
                    continue
                    
                strike_price = contract.strike_price
                contract_side = contract.side
                
                # Check if strike is within range and matches requested side
                if (min_strike <= strike_price <= max_strike and 
                    contract_side == side):
                    
                    # Format contract info
                    contract_info = {
                        'symbol': contract.symbol,
                        'underlying': symbol,
                        'strike': strike_price,
                        'expiration': contract.expiration_date,
                        'side': option_side,
                        'status': contract.status
                    }
                    
                    # Add additional info if available
                    if hasattr(contract, 'ask_price') and contract.ask_price:
                        contract_info['ask'] = contract.ask_price
                    if hasattr(contract, 'bid_price') and contract.bid_price:
                        contract_info['bid'] = contract.bid_price
                    if hasattr(contract, 'mid_price') and contract.mid_price:
                        contract_info['mid'] = contract.mid_price
                    elif 'ask' in contract_info and 'bid' in contract_info:
                        contract_info['mid'] = (contract_info['ask'] + contract_info['bid']) / 2
                        
                    atm_options.append(contract_info)
            
            # Sort by closest strike to current price
            atm_options.sort(key=lambda x: abs(x['strike'] - current_price))
            
            return atm_options
            
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}")
            return []
            
    except Exception as e:
        logger.error(f"Error finding ATM options for {symbol}: {e}")
        return []

def select_best_option_contract(
    symbol: str,
    signal_type: str,
    price_target: float,
    current_price: Optional[float] = None,
    risk_amount: float = 500.0
) -> Optional[Dict]:
    """
    Select the best option contract for a trading signal.
    
    Args:
        symbol: The underlying ticker symbol
        signal_type: Type of signal (breakout, breakdown, rejection, bounce)
        price_target: Target price for the signal
        current_price: Current price of the underlying (optional)
        risk_amount: Maximum risk amount in dollars
        
    Returns:
        Dictionary with selected option contract details or None if no suitable contract found
    """
    try:
        # Determine if we should use calls or puts based on signal type
        if signal_type in ["breakout", "bounce"]:
            option_side = "call"
        elif signal_type in ["breakdown", "rejection"]:
            option_side = "put"
        else:
            logger.warning(f"Unknown signal type: {signal_type}")
            option_side = "call"  # Default to calls
            
        # Get current price if not provided
        if current_price is None:
            stock_client = get_stock_data_client()
            if not stock_client:
                logger.error("Stock data client not initialized")
                return None
                
            # Get latest quote
            quote_response = stock_client.get_stock_latest_quote(symbol_or_symbols=symbol)
            if not quote_response or symbol not in quote_response:
                logger.error(f"Could not get latest quote for {symbol}")
                return None
                
            quote = quote_response[symbol]
            
            # Calculate mid price
            if not hasattr(quote, 'ask_price') or not hasattr(quote, 'bid_price'):
                logger.error(f"Invalid quote for {symbol}")
                return None
                
            current_price = (quote.ask_price + quote.bid_price) / 2
            
        # Find ATM options
        atm_options = find_atm_options(
            symbol=symbol,
            expiration_days=0,  # 0DTE
            option_side=option_side
        )
        
        if not atm_options:
            # Try with 1 day expiration if 0DTE not available
            atm_options = find_atm_options(
                symbol=symbol,
                expiration_days=1,
                option_side=option_side
            )
            
        if not atm_options:
            logger.warning(f"No suitable option contracts found for {symbol}")
            return None
            
        # Select the contract with strike closest to current price
        best_contract = atm_options[0]
        
        # Calculate quantity based on risk
        if 'mid' in best_contract:
            # Use mid price if available
            contract_price = best_contract['mid']
        elif 'ask' in best_contract:
            # Fall back to ask price
            contract_price = best_contract['ask']
        else:
            logger.warning(f"No price information for contract {best_contract['symbol']}")
            return None
            
        # Calculate quantity
        max_contracts = int(risk_amount / (contract_price * 100))
        quantity = max(1, max_contracts)  # At least 1 contract
        
        # Add quantity to contract info
        best_contract['quantity'] = quantity
        best_contract['signal_type'] = signal_type
        best_contract['price_target'] = price_target
        best_contract['current_price'] = current_price
        
        return best_contract
        
    except Exception as e:
        logger.error(f"Error selecting option contract for {symbol}: {e}")
        return None