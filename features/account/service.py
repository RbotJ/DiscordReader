"""
Account Service Layer

Centralized service for account operations, providing a clean interface
for account information, positions, portfolio analytics, and balance tracking
without exposing implementation details to API routes.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal

from features.account.info import get_account_service
from common.events.publisher import publish_event

logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Account information data."""
    account_id: str
    account_number: str
    status: str
    cash: Decimal
    portfolio_value: Decimal
    buying_power: Decimal
    equity: Decimal
    day_trade_count: int
    pattern_day_trader: bool
    created_at: datetime
    currency: str = "USD"


@dataclass
class Position:
    """Position data."""
    symbol: str
    quantity: int
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: float
    side: str  # 'long' or 'short'
    average_entry_price: Decimal


@dataclass
class PortfolioMetrics:
    """Portfolio analytics data."""
    total_value: Decimal
    cash_percent: float
    equity_percent: float
    day_change: Decimal
    day_change_percent: float
    total_pnl: Decimal
    total_pnl_percent: float
    largest_position_percent: float
    positions_count: int


class AccountService:
    """Service for account operations."""
    
    def __init__(self):
        self.account_provider = None
        
    def _get_account_provider(self):
        """Lazy load account provider."""
        if not self.account_provider:
            self.account_provider = get_account_service()
        return self.account_provider
    
    def get_account_info(self, force_refresh: bool = False) -> Optional[AccountInfo]:
        """
        Get account information.
        
        Args:
            force_refresh: Whether to force a refresh from the broker
            
        Returns:
            AccountInfo or None if not available
        """
        try:
            provider = self._get_account_provider()
            account_data = provider.get_account(force_refresh)
            
            if not account_data:
                logger.warning("No account data available")
                return None
            
            account = AccountInfo(
                account_id=account_data.get('id', ''),
                account_number=account_data.get('account_number', ''),
                status=account_data.get('status', 'unknown'),
                cash=Decimal(str(account_data.get('cash', 0))),
                portfolio_value=Decimal(str(account_data.get('portfolio_value', 0))),
                buying_power=Decimal(str(account_data.get('buying_power', 0))),
                equity=Decimal(str(account_data.get('equity', 0))),
                day_trade_count=int(account_data.get('daytrade_count', 0)),
                pattern_day_trader=account_data.get('pattern_day_trader', False),
                created_at=datetime.fromisoformat(account_data.get('created_at', datetime.now().isoformat())),
                currency=account_data.get('currency', 'USD')
            )
            
            # Publish account info event
            publish_event(
                event_type='account.info.retrieved',
                data={
                    'account_id': account.account_id,
                    'portfolio_value': float(account.portfolio_value),
                    'cash': float(account.cash),
                    'equity': float(account.equity),
                    'timestamp': datetime.now().isoformat()
                },
                channel='account:info',
                source='account_service'
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List of Position objects
        """
        try:
            provider = self._get_account_provider()
            positions_data = provider.get_positions()
            
            if not positions_data:
                logger.warning("No positions data available")
                return []
            
            positions = []
            for pos_data in positions_data:
                position = Position(
                    symbol=pos_data.get('symbol', '').upper(),
                    quantity=int(pos_data.get('qty', 0)),
                    market_value=Decimal(str(pos_data.get('market_value', 0))),
                    cost_basis=Decimal(str(pos_data.get('cost_basis', 0))),
                    unrealized_pnl=Decimal(str(pos_data.get('unrealized_pl', 0))),
                    unrealized_pnl_percent=float(pos_data.get('unrealized_plpc', 0)),
                    side=pos_data.get('side', 'long'),
                    average_entry_price=Decimal(str(pos_data.get('avg_entry_price', 0)))
                )
                positions.append(position)
            
            # Publish positions event
            publish_event(
                event_type='account.positions.retrieved',
                data={
                    'positions_count': len(positions),
                    'total_market_value': float(sum(p.market_value for p in positions)),
                    'symbols': [p.symbol for p in positions],
                    'timestamp': datetime.now().isoformat()
                },
                channel='account:positions',
                source='account_service'
            )
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_portfolio_metrics(self) -> Optional[PortfolioMetrics]:
        """
        Calculate portfolio analytics and metrics.
        
        Returns:
            PortfolioMetrics or None if calculation failed
        """
        try:
            # Get account info and positions
            account = self.get_account_info()
            positions = self.get_positions()
            
            if not account:
                return None
            
            # Calculate metrics
            total_value = account.portfolio_value
            cash_percent = float(account.cash / total_value * 100) if total_value > 0 else 0
            
            # Calculate equity percentage
            equity_value = sum(p.market_value for p in positions)
            equity_percent = float(equity_value / total_value * 100) if total_value > 0 else 0
            
            # Calculate day change (simplified - would need historical data)
            total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
            day_change = total_unrealized_pnl  # Simplified
            day_change_percent = float(day_change / (total_value - day_change) * 100) if total_value > day_change else 0
            
            # Calculate total P&L
            total_cost_basis = sum(p.cost_basis for p in positions)
            total_pnl = total_unrealized_pnl  # Only unrealized for now
            total_pnl_percent = float(total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
            
            # Find largest position
            largest_position_value = max((p.market_value for p in positions), default=Decimal(0))
            largest_position_percent = float(largest_position_value / total_value * 100) if total_value > 0 else 0
            
            metrics = PortfolioMetrics(
                total_value=total_value,
                cash_percent=cash_percent,
                equity_percent=equity_percent,
                day_change=day_change,
                day_change_percent=day_change_percent,
                total_pnl=total_pnl,
                total_pnl_percent=total_pnl_percent,
                largest_position_percent=largest_position_percent,
                positions_count=len(positions)
            )
            
            # Publish metrics event
            publish_event(
                event_type='account.metrics.calculated',
                data={
                    'total_value': float(metrics.total_value),
                    'cash_percent': metrics.cash_percent,
                    'equity_percent': metrics.equity_percent,
                    'day_change_percent': metrics.day_change_percent,
                    'positions_count': metrics.positions_count,
                    'timestamp': datetime.now().isoformat()
                },
                channel='account:metrics',
                source='account_service'
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return None
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position or None if not held
        """
        try:
            positions = self.get_positions()
            
            for position in positions:
                if position.symbol.upper() == symbol.upper():
                    return position
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {e}")
            return None
    
    def calculate_position_risk(self, symbol: str, quantity: int, price: Decimal) -> Dict[str, Any]:
        """
        Calculate risk metrics for a potential position.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            
        Returns:
            Dictionary with risk metrics
        """
        try:
            account = self.get_account_info()
            if not account:
                return {}
            
            # Calculate position value
            position_value = quantity * price
            
            # Calculate as percentage of portfolio
            portfolio_percent = float(position_value / account.portfolio_value * 100) if account.portfolio_value > 0 else 0
            
            # Calculate impact on buying power
            buying_power_impact = float(position_value / account.buying_power * 100) if account.buying_power > 0 else 0
            
            # Get current position if exists
            current_position = self.get_position_by_symbol(symbol)
            
            risk_metrics = {
                'position_value': float(position_value),
                'portfolio_percent': portfolio_percent,
                'buying_power_impact': buying_power_impact,
                'current_position_value': float(current_position.market_value) if current_position else 0,
                'would_exceed_5_percent': portfolio_percent > 5.0,
                'would_exceed_10_percent': portfolio_percent > 10.0,
                'available_buying_power': float(account.buying_power),
                'sufficient_buying_power': position_value <= account.buying_power
            }
            
            # Publish risk calculation event
            publish_event(
                event_type='account.risk.calculated',
                data={
                    'symbol': symbol.upper(),
                    'quantity': quantity,
                    'price': float(price),
                    'portfolio_percent': portfolio_percent,
                    'sufficient_buying_power': risk_metrics['sufficient_buying_power'],
                    'timestamp': datetime.now().isoformat()
                },
                channel='account:risk',
                source='account_service'
            )
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating position risk for {symbol}: {e}")
            return {}
    
    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive account summary.
        
        Returns:
            Dictionary with account summary data
        """
        try:
            account = self.get_account_info()
            positions = self.get_positions()
            metrics = self.get_portfolio_metrics()
            
            if not account:
                return {}
            
            # Top holdings
            top_holdings = sorted(positions, key=lambda x: x.market_value, reverse=True)[:5]
            
            summary = {
                'account': {
                    'id': account.account_id,
                    'status': account.status,
                    'pattern_day_trader': account.pattern_day_trader,
                    'day_trade_count': account.day_trade_count
                },
                'balance': {
                    'cash': float(account.cash),
                    'portfolio_value': float(account.portfolio_value),
                    'buying_power': float(account.buying_power),
                    'equity': float(account.equity)
                },
                'positions': {
                    'count': len(positions),
                    'total_value': float(sum(p.market_value for p in positions)),
                    'top_holdings': [
                        {
                            'symbol': p.symbol,
                            'quantity': p.quantity,
                            'market_value': float(p.market_value),
                            'unrealized_pnl': float(p.unrealized_pnl)
                        }
                        for p in top_holdings
                    ]
                },
                'metrics': {
                    'cash_percent': metrics.cash_percent if metrics else 0,
                    'day_change_percent': metrics.day_change_percent if metrics else 0,
                    'total_pnl_percent': metrics.total_pnl_percent if metrics else 0
                } if metrics else {}
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating account summary: {e}")
            return {}


# Global service instance
_account_service = None


def get_account_service() -> AccountService:
    """Get the account service instance."""
    global _account_service
    if _account_service is None:
        _account_service = AccountService()
    return _account_service