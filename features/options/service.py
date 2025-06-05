"""
Options Service Layer

Centralized service for options operations, providing a clean interface
for options chains, pricing, contract selection, and risk assessment
without exposing implementation details to API routes.
"""
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from features.options.pricing import get_options_pricing
from common.events.publisher import publish_event

logger = logging.getLogger(__name__)


@dataclass
class OptionContract:
    """Options contract data."""
    symbol: str
    underlying_symbol: str
    expiration_date: date
    strike_price: float
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


@dataclass
class OptionChain:
    """Options chain data."""
    underlying_symbol: str
    expiration_date: Optional[date]
    calls: List[OptionContract]
    puts: List[OptionContract]
    underlying_price: Optional[float] = None


@dataclass
class OptionSelection:
    """Selected option contracts for a strategy."""
    contracts: List[OptionContract]
    strategy_type: str
    total_cost: float
    max_profit: Optional[float]
    max_loss: Optional[float]
    breakeven_points: List[float]


class OptionsService:
    """Service for options operations."""
    
    def __init__(self):
        self.pricing_service = None
        
    def _get_pricing_service(self):
        """Lazy load options pricing service."""
        if not self.pricing_service:
            self.pricing_service = get_options_pricing()
        return self.pricing_service
    
    def get_option_chain(self, symbol: str, expiration: Optional[str] = None) -> Optional[OptionChain]:
        """
        Get option chain for a symbol.
        
        Args:
            symbol: Underlying symbol
            expiration: Optional expiration date (YYYY-MM-DD format)
            
        Returns:
            OptionChain or None if not available
        """
        try:
            pricing = self._get_pricing_service()
            
            # Parse expiration date if provided
            exp_date = None
            if expiration:
                exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
            
            # Get raw chain data
            chain_data = pricing.get_option_chain(symbol, expiration)
            
            if not chain_data:
                logger.warning(f"No option chain data available for {symbol}")
                return None
            
            # Convert to structured data
            calls = []
            puts = []
            
            for contract_data in chain_data:
                contract = OptionContract(
                    symbol=contract_data.get('symbol', ''),
                    underlying_symbol=symbol.upper(),
                    expiration_date=datetime.strptime(contract_data.get('expiration_date', ''), '%Y-%m-%d').date(),
                    strike_price=float(contract_data.get('strike_price', 0)),
                    option_type=contract_data.get('option_type', '').lower(),
                    bid=float(contract_data.get('bid', 0)),
                    ask=float(contract_data.get('ask', 0)),
                    last=float(contract_data.get('last', 0)),
                    volume=int(contract_data.get('volume', 0)),
                    open_interest=int(contract_data.get('open_interest', 0)),
                    implied_volatility=contract_data.get('implied_volatility'),
                    delta=contract_data.get('delta'),
                    gamma=contract_data.get('gamma'),
                    theta=contract_data.get('theta'),
                    vega=contract_data.get('vega')
                )
                
                if contract.option_type == 'call':
                    calls.append(contract)
                elif contract.option_type == 'put':
                    puts.append(contract)
            
            # Sort by strike price
            calls.sort(key=lambda x: x.strike_price)
            puts.sort(key=lambda x: x.strike_price)
            
            chain = OptionChain(
                underlying_symbol=symbol.upper(),
                expiration_date=exp_date,
                calls=calls,
                puts=puts,
                underlying_price=chain_data[0].get('underlying_price') if chain_data else None
            )
            
            # Publish chain retrieval event
            publish_event(
                event_type='options.chain.retrieved',
                data={
                    'symbol': symbol.upper(),
                    'expiration': expiration,
                    'calls_count': len(calls),
                    'puts_count': len(puts),
                    'timestamp': datetime.now().isoformat()
                },
                channel='options:chains',
                source='options_service'
            )
            
            return chain
            
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}")
            return None
    
    def get_contract_quote(self, contract_symbol: str) -> Optional[OptionContract]:
        """
        Get current quote for an options contract.
        
        Args:
            contract_symbol: Options contract symbol
            
        Returns:
            OptionContract or None if not available
        """
        try:
            pricing = self._get_pricing_service()
            quote_data = pricing.get_contract_quote(contract_symbol)
            
            if not quote_data:
                logger.warning(f"No quote data available for {contract_symbol}")
                return None
            
            contract = OptionContract(
                symbol=contract_symbol,
                underlying_symbol=quote_data.get('underlying_symbol', ''),
                expiration_date=datetime.strptime(quote_data.get('expiration_date', ''), '%Y-%m-%d').date(),
                strike_price=float(quote_data.get('strike_price', 0)),
                option_type=quote_data.get('option_type', '').lower(),
                bid=float(quote_data.get('bid', 0)),
                ask=float(quote_data.get('ask', 0)),
                last=float(quote_data.get('last', 0)),
                volume=int(quote_data.get('volume', 0)),
                open_interest=int(quote_data.get('open_interest', 0)),
                implied_volatility=quote_data.get('implied_volatility'),
                delta=quote_data.get('delta'),
                gamma=quote_data.get('gamma'),
                theta=quote_data.get('theta'),
                vega=quote_data.get('vega')
            )
            
            # Publish quote event
            publish_event(
                event_type='options.quote.retrieved',
                data={
                    'symbol': contract_symbol,
                    'underlying': contract.underlying_symbol,
                    'price': contract.last,
                    'timestamp': datetime.now().isoformat()
                },
                channel='options:quotes',
                source='options_service'
            )
            
            return contract
            
        except Exception as e:
            logger.error(f"Error getting contract quote for {contract_symbol}: {e}")
            return None
    
    def find_contracts_by_criteria(self, symbol: str, criteria: Dict[str, Any]) -> List[OptionContract]:
        """
        Find option contracts matching specific criteria.
        
        Args:
            symbol: Underlying symbol
            criteria: Search criteria (e.g., min_volume, max_strike, option_type)
            
        Returns:
            List of matching OptionContract
        """
        try:
            # Get the full option chain
            chain = self.get_option_chain(symbol)
            
            if not chain:
                return []
            
            # Combine calls and puts
            all_contracts = chain.calls + chain.puts
            
            # Apply filters
            filtered_contracts = all_contracts
            
            if 'option_type' in criteria:
                option_type = criteria['option_type'].lower()
                filtered_contracts = [c for c in filtered_contracts if c.option_type == option_type]
            
            if 'min_volume' in criteria:
                min_vol = int(criteria['min_volume'])
                filtered_contracts = [c for c in filtered_contracts if c.volume >= min_vol]
            
            if 'max_strike' in criteria:
                max_strike = float(criteria['max_strike'])
                filtered_contracts = [c for c in filtered_contracts if c.strike_price <= max_strike]
            
            if 'min_strike' in criteria:
                min_strike = float(criteria['min_strike'])
                filtered_contracts = [c for c in filtered_contracts if c.strike_price >= min_strike]
            
            if 'max_days_to_expiry' in criteria:
                max_days = int(criteria['max_days_to_expiry'])
                cutoff_date = date.today()
                from datetime import timedelta
                cutoff_date += timedelta(days=max_days)
                filtered_contracts = [c for c in filtered_contracts if c.expiration_date <= cutoff_date]
            
            # Sort by volume (most liquid first)
            filtered_contracts.sort(key=lambda x: x.volume, reverse=True)
            
            # Publish search event
            publish_event(
                event_type='options.search.completed',
                data={
                    'symbol': symbol.upper(),
                    'criteria': criteria,
                    'results_count': len(filtered_contracts),
                    'timestamp': datetime.now().isoformat()
                },
                channel='options:search',
                source='options_service'
            )
            
            return filtered_contracts
            
        except Exception as e:
            logger.error(f"Error finding contracts for {symbol}: {e}")
            return []
    
    def calculate_strategy_payoff(self, contracts: List[OptionContract], 
                                 underlying_prices: List[float]) -> Dict[str, Any]:
        """
        Calculate payoff for an options strategy at different underlying prices.
        
        Args:
            contracts: List of option contracts in the strategy
            underlying_prices: List of underlying prices to calculate payoff for
            
        Returns:
            Dictionary with payoff analysis
        """
        try:
            payoffs = []
            
            for price in underlying_prices:
                total_payoff = 0.0
                
                for contract in contracts:
                    # Calculate intrinsic value at expiration
                    if contract.option_type == 'call':
                        intrinsic = max(0, price - contract.strike_price)
                    else:  # put
                        intrinsic = max(0, contract.strike_price - price)
                    
                    # Subtract premium paid (using last price as proxy)
                    net_payoff = intrinsic - contract.last
                    total_payoff += net_payoff
                
                payoffs.append({
                    'underlying_price': price,
                    'total_payoff': total_payoff
                })
            
            # Find breakeven points (where payoff = 0)
            breakevens = []
            for i in range(len(payoffs) - 1):
                curr_payoff = payoffs[i]['total_payoff']
                next_payoff = payoffs[i + 1]['total_payoff']
                
                if (curr_payoff <= 0 <= next_payoff) or (next_payoff <= 0 <= curr_payoff):
                    # Linear interpolation to find exact breakeven
                    curr_price = payoffs[i]['underlying_price']
                    next_price = payoffs[i + 1]['underlying_price']
                    
                    if next_payoff != curr_payoff:
                        breakeven = curr_price - curr_payoff * (next_price - curr_price) / (next_payoff - curr_payoff)
                        breakevens.append(breakeven)
            
            # Calculate max profit/loss
            all_payoffs = [p['total_payoff'] for p in payoffs]
            max_profit = max(all_payoffs) if all_payoffs else 0
            max_loss = min(all_payoffs) if all_payoffs else 0
            
            analysis = {
                'payoffs': payoffs,
                'breakeven_points': breakevens,
                'max_profit': max_profit if max_profit > 0 else None,
                'max_loss': abs(max_loss) if max_loss < 0 else None,
                'total_premium': sum(c.last for c in contracts)
            }
            
            # Publish analysis event
            publish_event(
                event_type='options.strategy.analyzed',
                data={
                    'contracts_count': len(contracts),
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'breakeven_count': len(breakevens),
                    'timestamp': datetime.now().isoformat()
                },
                channel='options:analysis',
                source='options_service'
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error calculating strategy payoff: {e}")
            return {}
    
    def suggest_contracts_for_signal(self, signal_data: Dict[str, Any]) -> Optional[OptionSelection]:
        """
        Suggest option contracts for a trading signal.
        
        Args:
            signal_data: Trading signal information
            
        Returns:
            OptionSelection or None if no suitable contracts found
        """
        try:
            symbol = signal_data.get('symbol', '').upper()
            direction = signal_data.get('direction', '').lower()  # 'bullish' or 'bearish'
            confidence = signal_data.get('confidence', 0.5)
            
            if not symbol or not direction:
                logger.error("Symbol and direction required for contract suggestion")
                return None
            
            # Define search criteria based on signal
            criteria = {
                'min_volume': 10,  # Minimum liquidity
                'max_days_to_expiry': 45  # Near-term options
            }
            
            if direction == 'bullish':
                criteria['option_type'] = 'call'
            elif direction == 'bearish':
                criteria['option_type'] = 'put'
            else:
                logger.error(f"Unsupported direction: {direction}")
                return None
            
            # Find suitable contracts
            contracts = self.find_contracts_by_criteria(symbol, criteria)
            
            if not contracts:
                logger.warning(f"No suitable contracts found for {symbol}")
                return None
            
            # Select contracts based on confidence level
            # Higher confidence = closer to ATM, lower confidence = further OTM
            if confidence > 0.7:
                # High confidence: ATM options
                selected = contracts[:3]  # Top 3 most liquid
            elif confidence > 0.5:
                # Medium confidence: slightly OTM
                selected = contracts[2:5] if len(contracts) > 4 else contracts[-2:]
            else:
                # Low confidence: further OTM
                selected = contracts[-3:] if len(contracts) > 2 else contracts
            
            if not selected:
                return None
            
            # Calculate strategy metrics
            total_cost = sum(c.ask for c in selected)  # Use ask price for buying
            
            selection = OptionSelection(
                contracts=selected,
                strategy_type=f"{direction}_directional",
                total_cost=total_cost,
                max_profit=None,  # Would need payoff calculation
                max_loss=total_cost,  # Maximum loss is premium paid
                breakeven_points=[]  # Would need detailed calculation
            )
            
            # Publish suggestion event
            publish_event(
                event_type='options.contracts.suggested',
                data={
                    'symbol': symbol,
                    'direction': direction,
                    'confidence': confidence,
                    'contracts_count': len(selected),
                    'total_cost': total_cost,
                    'timestamp': datetime.now().isoformat()
                },
                channel='options:suggestions',
                source='options_service'
            )
            
            return selection
            
        except Exception as e:
            logger.error(f"Error suggesting contracts for signal: {e}")
            return None


# Global service instance
_options_service = None


def get_options_service() -> OptionsService:
    """Get the options service instance."""
    global _options_service
    if _options_service is None:
        _options_service = OptionsService()
    return _options_service