"""
Options Contract Selector Module

This module provides intelligent selection of options contracts based on
trading signals, price levels, and risk parameters. It integrates with
the options pricing service to find optimal contracts to trade.
"""
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, date

from features.options.pricing import get_options_pricing
from features.market.history import get_history_provider

# Configure logger
logger = logging.getLogger(__name__)

class OptionsContractSelector:
    """
    Service for selecting optimal options contracts based on trading signals.
    """
    
    def __init__(self):
        """Initialize the options contract selector."""
        self.options_pricing = get_options_pricing()
        self.history_provider = get_history_provider()
        
    def select_contract_for_signal(
        self,
        symbol: str,
        signal_type: str,
        price_level: float,
        risk_amount: float = 500.0,
        expiration_date: Optional[Union[str, date]] = None,
        aggressiveness: str = "medium"
    ) -> Optional[Dict]:
        """
        Select the optimal options contract based on a trading signal.
        
        Args:
            symbol: Underlying ticker symbol
            signal_type: Signal type ('breakout', 'breakdown', 'rejection', 'bounce')
            price_level: Price level for the signal
            risk_amount: Maximum risk amount per trade
            expiration_date: Expiration date (optional, defaults to 0 DTE)
            aggressiveness: Trade aggressiveness ('conservative', 'medium', 'aggressive')
            
        Returns:
            Dict with selected contract data or None if no suitable contract found
        """
        try:
            # Determine direction based on signal type
            if signal_type.lower() in ['breakout', 'bounce']:
                direction = 'call'
            elif signal_type.lower() in ['breakdown', 'rejection']:
                direction = 'put'
            else:
                logger.warning(f"Unknown signal type: {signal_type}")
                return None
                
            # Get current market price
            latest_data = self.history_provider.get_candles(symbol, '1m', limit=1)
            if not latest_data or not latest_data[0]:
                logger.warning(f"Could not get latest price for {symbol}")
                return None
                
            current_price = latest_data[0]['close']
            
            # Determine strike selection based on signal type and aggressiveness
            strikes_above = 0
            strikes_below = 0
            
            if direction == 'call':
                # For calls, look above current price for breakouts/bounces
                if aggressiveness == 'conservative':
                    # ATM or slightly ITM
                    strikes_above = 0
                    strikes_below = 1
                elif aggressiveness == 'medium':
                    # ATM
                    strikes_above = 0
                    strikes_below = 0
                else:  # aggressive
                    # OTM
                    strikes_above = 1
                    strikes_below = 0
            else:  # put
                # For puts, look below current price for breakdowns/rejections
                if aggressiveness == 'conservative':
                    # ATM or slightly ITM
                    strikes_above = 1
                    strikes_below = 0
                elif aggressiveness == 'medium':
                    # ATM
                    strikes_above = 0
                    strikes_below = 0
                else:  # aggressive
                    # OTM
                    strikes_above = 0
                    strikes_below = 1
                    
            # Get near-the-money options (preferably 0 DTE)
            if expiration_date:
                options_data = self.options_pricing.get_near_the_money_options(
                    symbol,
                    expiration_date,
                    num_strikes=3,
                    underlying_price=current_price
                )
            else:
                options_data = self.options_pricing.get_odte_options(
                    symbol,
                    num_strikes=3
                )
                
            if not options_data:
                logger.warning(f"No options data found for {symbol}")
                return None
                
            # Select contracts based on direction
            contracts = options_data['calls'] if direction == 'call' else options_data['puts']
            
            if not contracts:
                logger.warning(f"No {direction} contracts found for {symbol}")
                return None
                
            # Sort contracts by strike
            contracts.sort(key=lambda x: x['strike_price'])
            
            # Find the ATM contract (closest to current price)
            atm_idx = min(range(len(contracts)), 
                         key=lambda i: abs(contracts[i]['strike_price'] - current_price))
            
            # Select contract based on aggressiveness
            selected_idx = atm_idx
            
            if direction == 'call':
                if aggressiveness == 'conservative':
                    # Slightly ITM call
                    selected_idx = max(0, atm_idx - 1)
                elif aggressiveness == 'aggressive':
                    # OTM call
                    selected_idx = min(len(contracts) - 1, atm_idx + 1)
            else:  # put
                if aggressiveness == 'conservative':
                    # Slightly ITM put
                    selected_idx = min(len(contracts) - 1, atm_idx + 1)
                elif aggressiveness == 'aggressive':
                    # OTM put
                    selected_idx = max(0, atm_idx - 1)
                    
            # Get the selected contract
            contract = contracts[selected_idx]
            
            # Calculate position size based on risk amount
            position_size = self._calculate_position_size(contract, risk_amount)
            
            # Add trade details to the contract
            contract['direction'] = direction
            contract['position_size'] = position_size
            contract['signal_type'] = signal_type
            contract['price_level'] = price_level
            contract['aggressiveness'] = aggressiveness
            contract['risk_amount'] = risk_amount
            contract['cost_basis'] = round(position_size * 100 * (contract.get('ask') or 0), 2)
            
            return contract
        except Exception as e:
            logger.error(f"Error selecting contract for {symbol} {signal_type}: {e}", exc_info=True)
            return None
    
    def _calculate_position_size(self, contract: Dict, risk_amount: float) -> int:
        """
        Calculate the number of contracts to trade based on risk amount.
        
        Args:
            contract: Option contract data
            risk_amount: Maximum risk amount
            
        Returns:
            Number of contracts to trade
        """
        # Use ask price if available, otherwise use last price or default
        contract_price = contract.get('ask') or contract.get('last') or 1.0
        
        # Calculate how many contracts we can buy with the risk amount
        # Each contract is for 100 shares
        max_contracts = int(risk_amount / (contract_price * 100))
        
        # Always trade at least 1 contract
        return max(1, max_contracts)
        
    def select_contracts_for_ticker(
        self,
        symbol: str,
        signals: List[Dict],
        risk_total: float = 1000.0
    ) -> List[Dict]:
        """
        Select multiple contracts based on multiple signals for a ticker.
        
        Args:
            symbol: Underlying ticker symbol
            signals: List of signal dictionaries (each containing type, price_level, etc.)
            risk_total: Total risk amount to allocate across all signals
            
        Returns:
            List of selected contracts
        """
        if not signals:
            return []
            
        # Allocate risk amount per signal
        risk_per_signal = risk_total / len(signals)
        
        # Select contracts for each signal
        contracts = []
        for signal in signals:
            contract = self.select_contract_for_signal(
                symbol,
                signal.get('category', 'unknown'),
                signal.get('trigger', {}).get('price', 0.0),
                risk_per_signal,
                aggressiveness=signal.get('aggressiveness', 'medium')
            )
            
            if contract:
                # Add signal details to contract
                contract['signal_id'] = signal.get('id')
                contracts.append(contract)
                
        return contracts
        
    def get_option_trading_parameters(
        self,
        symbol: str,
        direction: str,
        expiration: Optional[str] = None,
        strike_price: Optional[float] = None,
        quantity: int = 1
    ) -> Dict:
        """
        Get full trading parameters for an option contract.
        
        Args:
            symbol: Underlying ticker symbol
            direction: 'call' or 'put'
            expiration: Expiration date (YYYY-MM-DD)
            strike_price: Strike price
            quantity: Number of contracts to trade
            
        Returns:
            Dict with all trading parameters
        """
        # If no expiration specified, get nearest
        if not expiration:
            exp_date = self.options_pricing.get_nearest_expiration(symbol)
            if exp_date:
                expiration = exp_date.isoformat()
            else:
                logger.warning(f"Could not determine expiration for {symbol}")
                return {}
                
        # If no strike specified, get ATM
        if not strike_price:
            latest_data = self.history_provider.get_candles(symbol, '1m', limit=1)
            if latest_data and latest_data[0]:
                current_price = latest_data[0]['close']
                
                # Get near-the-money options
                options = self.options_pricing.get_near_the_money_options(
                    symbol,
                    expiration,
                    num_strikes=1,
                    underlying_price=current_price
                )
                
                if options:
                    contracts = options['calls'] if direction == 'call' else options['puts']
                    if contracts:
                        # Use the middle (ATM) contract
                        contract = contracts[len(contracts) // 2]
                        strike_price = contract['strike_price']
                        
        if not strike_price:
            logger.warning(f"Could not determine strike price for {symbol}")
            return {}
            
        # Format strike price for the option symbol
        strike_str = f"{strike_price:.2f}".replace('.', '')
        
        # Build option symbol (OCC format)
        option_type = 'C' if direction.lower() == 'call' else 'P'
        expiration_date = expiration.replace('-', '')
        option_symbol = f"{symbol}{expiration_date}{option_type}{strike_str}"
        
        return {
            "symbol": option_symbol,
            "underlying": symbol,
            "quantity": quantity,
            "direction": direction,
            "expiration": expiration,
            "strike_price": strike_price
        }

# Global instance
options_selector = OptionsContractSelector()

def get_options_selector() -> OptionsContractSelector:
    """
    Get the global options contract selector instance.
    
    Returns:
        OptionsContractSelector instance
    """
    return options_selector