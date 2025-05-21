"""
Account Information Module

This module provides access to account-related information from Alpaca's API,
including account balance, buying power, and position data.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta

from features.alpaca.client import (
    get_account_info, get_positions, get_orders, get_open_orders
)

# Configure logger
logger = logging.getLogger(__name__)

class AccountInfoService:
    """
    Service for retrieving and analyzing account information.
    """
    
    def __init__(self):
        """Initialize the account information service."""
        self.account_cache = None
        self.positions_cache = None
        self.orders_cache = None
        self.cache_timestamp = None
        self.cache_ttl = 60  # Cache TTL in seconds
        
    def get_account(self, force_refresh: bool = False) -> Dict:
        """
        Get account information from Alpaca.
        
        Args:
            force_refresh: Whether to force a refresh of the cache
            
        Returns:
            Dict containing account information with market status
        """
        # Check if cached data is still valid
        if not force_refresh and self.account_cache and self.cache_timestamp:
            elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
            if elapsed < self.cache_ttl:
                # Cache is still valid
                return self.account_cache

        from features.alpaca.client import get_trading_client, get_market_clock
                
        # Get fresh account data
        client = get_trading_client()
        if not client:
            return {}
            
        try:
            account = client.get_account()
            clock = get_market_clock()
            
            self.account_cache = {
                'id': account.id,
                'account_number': account.account_number,
                'status': account.status,
                'currency': account.currency,
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'position_market_value': float(account.position_market_value),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked,
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'market': {
                    'is_open': clock.get('is_open', False),
                    'next_open': clock.get('next_open'),
                    'next_close': clock.get('next_close'),
                    'timestamp': clock.get('timestamp')
                }
            }
            
            self.cache_timestamp = datetime.now()
            
            return self.account_cache
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
        
    def get_positions(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get current positions from Alpaca.
        
        Args:
            force_refresh: Whether to force a refresh of the cache
            
        Returns:
            List of position dictionaries
        """
        # Check if cached data is still valid
        if not force_refresh and self.positions_cache and self.cache_timestamp:
            elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
            if elapsed < self.cache_ttl:
                # Cache is still valid
                return self.positions_cache
                
        # Get fresh data
        self.positions_cache = get_positions()
        self.cache_timestamp = datetime.now()
        
        return self.positions_cache or []
        
    def get_orders(self, status: str = 'open', force_refresh: bool = False) -> List[Dict]:
        """
        Get orders from Alpaca.
        
        Args:
            status: Order status ('open', 'closed', 'all')
            force_refresh: Whether to force a refresh of the cache
            
        Returns:
            List of order dictionaries
        """
        # Check if cached data is still valid for open orders
        # (closed orders don't change, so no need to refresh)
        if status == 'open' and not force_refresh and self.orders_cache and self.cache_timestamp:
            elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
            if elapsed < self.cache_ttl:
                # Cache is still valid
                return self.orders_cache
                
        # Get fresh data
        orders = get_orders(status)
        
        # Update cache for open orders
        if status == 'open':
            self.orders_cache = orders
            self.cache_timestamp = datetime.now()
            
        return orders or []
        
    def get_buying_power(self) -> float:
        """
        Get available buying power from the account.
        
        Returns:
            Available buying power in dollars
        """
        account = self.get_account()
        return float(account.get('buying_power', 0))
        
    def get_equity(self) -> float:
        """
        Get current equity value from the account.
        
        Returns:
            Equity value in dollars
        """
        account = self.get_account()
        return float(account.get('equity', 0))
        
    def get_cash(self) -> float:
        """
        Get available cash from the account.
        
        Returns:
            Available cash in dollars
        """
        account = self.get_account()
        return float(account.get('cash', 0))
        
    def get_position_value(self) -> float:
        """
        Get total value of open positions.
        
        Returns:
            Total position value in dollars
        """
        account = self.get_account()
        return float(account.get('position_value', 0))
        
    def get_portfolio_value_history(self, days: int = 30) -> List[Dict]:
        """
        Get portfolio value history for the specified number of days.
        
        Note: This implementation makes multiple calls to the Alpaca API to retrieve
        account information at different time intervals. In a production environment,
        you would want to store this data in a database as it's collected.
        
        Args:
            days: Number of days of history to retrieve
            
        Returns:
            List of historical portfolio values
        """
        # Get current equity value
        current_equity = self.get_equity()
        
        # In a real implementation, we would access historical account data
        # stored in a database. For now, we'll return the current equity
        # as the value for all historical dates.
        result = []
        for i in range(days):
            date_value = (datetime.now() - timedelta(days=i)).date().isoformat() 
            result.append({
                'date': date_value,
                'value': current_equity
            })
            
        return result
        
    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Get position data for a specific symbol.
        
        Args:
            symbol: Symbol to get position for
            
        Returns:
            Position dictionary or None if not found
        """
        positions = self.get_positions()
        
        for position in positions:
            if position.get('symbol') == symbol:
                return position
                
        return None
        
    def calculate_portfolio_allocation(self) -> Dict[str, float]:
        """
        Calculate portfolio allocation percentages by symbol.
        
        Returns:
            Dict mapping symbols to allocation percentages
        """
        positions = self.get_positions()
        total_value = self.get_position_value()
        
        if total_value <= 0 or not positions:
            return {}
            
        allocation = {}
        for position in positions:
            symbol = position.get('symbol')
            market_value = float(position.get('market_value', 0))
            allocation[symbol] = (market_value / total_value) * 100
            
        return allocation
        
    def get_daily_pnl(self) -> float:
        """
        Get daily profit and loss.
        
        Returns:
            Daily profit/loss in dollars
        """
        account = self.get_account()
        return float(account.get('equity_change', 0))
        
    def get_risk_metrics(self) -> Dict:
        """
        Calculate risk metrics for the account.
        
        Returns:
            Dict with risk metrics
        """
        # Get required data
        account = self.get_account()
        positions = self.get_positions()
        
        # Calculate basic metrics
        equity = float(account.get('equity', 0))
        cash = float(account.get('cash', 0))
        
        # Cash allocation (percentage of portfolio in cash)
        cash_allocation = (cash / equity * 100) if equity > 0 else 0
        
        # Position concentration (largest position as percentage of equity)
        max_position_value = 0
        max_position_symbol = None
        
        for position in positions:
            market_value = float(position.get('market_value', 0))
            if market_value > max_position_value:
                max_position_value = market_value
                max_position_symbol = position.get('symbol')
                
        concentration = (max_position_value / equity * 100) if equity > 0 else 0
        
        # Count how many positions we have
        position_count = len(positions)
        
        return {
            'cash_allocation': cash_allocation,
            'largest_position': {
                'symbol': max_position_symbol,
                'value': max_position_value,
                'percentage': concentration
            },
            'position_count': position_count
        }
        
    def get_daily_activity(self) -> List[Dict]:
        """
        Get today's trading activity.
        
        Returns:
            List of activity dictionaries for today
        """
        # Get closed orders for today
        orders = get_orders('closed')
        
        today = datetime.now().date()
        
        # Filter to just today's orders
        today_orders = []
        for order in orders:
            created_at = order.get('created_at')
            if created_at:
                try:
                    # Parse the timestamp string
                    if isinstance(created_at, str):
                        order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                    else:
                        order_date = created_at.date()
                        
                    if order_date == today:
                        today_orders.append(order)
                except (ValueError, AttributeError):
                    # Skip orders with invalid timestamps
                    continue
                    
        return today_orders

# Global instance
account_service = AccountInfoService()

def get_account_service() -> AccountInfoService:
    """
    Get the global account information service instance.
    
    Returns:
        AccountInfoService instance
    """
    return account_service