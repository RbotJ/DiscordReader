"""
Dashboard Data Service

This module provides data access services for the dashboard feature.
It centralizes data retrieval logic for all dashboard views.
"""

import logging
import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# Setup logging
logger = logging.getLogger(__name__)

def get_dashboard_summary() -> Dict[str, Any]:
    """
    Get summary data for the main dashboard.
    
    Returns:
        Dictionary containing summary data for the dashboard
    """
    try:
        # Import necessary services from other features
        from features.account.info import get_account_info
        from features.market.api import get_market_status
        
        # Get account information
        account_info = get_account_info()
        
        # Get market status
        market_status = get_market_status()
        
        # Get active setups count from the database
        from features.setups.service import get_active_setups_count
        active_setups = get_active_setups_count()
        
        # Get active positions
        from features.execution.api_routes import get_active_positions
        positions = get_active_positions()
        
        return {
            'account': account_info,
            'market': market_status,
            'active_setups_count': active_setups,
            'positions_count': len(positions),
            'updated_at': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        # Return minimal data structure to avoid breaking the UI
        return {
            'account': {},
            'market': {},
            'active_setups_count': 0,
            'positions_count': 0,
            'updated_at': datetime.datetime.now().isoformat(),
            'error': str(e)
        }

def get_discord_stats() -> Dict[str, Any]:
    """
    Get Discord message statistics.
    
    Returns:
        Dictionary containing Discord stats
    """
    try:
        # Import the necessary service from discord feature
        from features.discord.message_publisher import get_message_stats
        
        # Get message statistics
        stats = get_message_stats()
        
        # Get recent messages
        from features.discord.message_consumer import get_recent_messages
        recent_messages = get_recent_messages(limit=10)
        
        return {
            'stats': stats,
            'recent_messages': recent_messages,
            'updated_at': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Discord stats: {e}")
        return {
            'stats': {},
            'recent_messages': [],
            'updated_at': datetime.datetime.now().isoformat(),
            'error': str(e)
        }

def get_trade_monitor_data() -> Dict[str, Any]:
    """
    Get data for trade monitoring.
    
    Returns:
        Dictionary containing trade monitoring data
    """
    try:
        # Import necessary services
        from features.execution.api_routes import get_active_positions
        from features.alpaca.position_management import get_position_details
        
        # Get active positions
        positions = get_active_positions()
        
        # Get position details
        position_details = []
        for position in positions:
            details = get_position_details(position['symbol'])
            position_details.append(details)
        
        # Get recent trades
        from features.execution.trader import get_recent_trades
        recent_trades = get_recent_trades(limit=20)
        
        return {
            'positions': position_details,
            'recent_trades': recent_trades,
            'updated_at': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting trade monitor data: {e}")
        return {
            'positions': [],
            'recent_trades': [],
            'updated_at': datetime.datetime.now().isoformat(),
            'error': str(e)
        }

def get_setup_data() -> Dict[str, Any]:
    """
    Get data for setup monitoring.
    
    Returns:
        Dictionary containing setup monitoring data
    """
    try:
        # Import necessary services
        from features.setups.service import get_active_setups
        from features.strategy.monitor import get_active_signals
        
        # Get active setups
        setups = get_active_setups()
        
        # Get active signals
        signals = get_active_signals()
        
        # Get active tickers
        tickers = list(set([setup['symbol'] for setup in setups]))
        
        # Get market data for active tickers
        from features.market.api import get_latest_prices
        prices = get_latest_prices(tickers) if tickers else {}
        
        return {
            'setups': setups,
            'signals': signals,
            'prices': prices,
            'tickers': tickers,
            'updated_at': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting setup data: {e}")
        return {
            'setups': [],
            'signals': [],
            'prices': {},
            'tickers': [],
            'updated_at': datetime.datetime.now().isoformat(),
            'error': str(e)
        }

def get_daily_performance(date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Get daily ticker performance data.
    
    Args:
        date_str: Optional date string in YYYY-MM-DD format
                 If not provided, use current date.
    
    Returns:
        Dictionary containing daily performance data
    """
    try:
        # Set default date to today if not provided
        if not date_str:
            today = datetime.datetime.now().date()
            date_str = today.isoformat()
        
        # Import necessary services
        from features.market.history import get_daily_performance
        from features.setups.service import get_setups_by_date
        
        # Get daily performance data
        performance_data = get_daily_performance(date_str)
        
        # Get setups for the date
        setups = get_setups_by_date(date_str)
        
        # Get active tickers for the date
        tickers = list(set([setup['symbol'] for setup in setups]))
        
        return {
            'date': date_str,
            'performance': performance_data,
            'setups': setups,
            'tickers': tickers,
            'updated_at': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting daily performance data: {e}")
        return {
            'date': date_str or datetime.datetime.now().date().isoformat(),
            'performance': [],
            'setups': [],
            'tickers': [],
            'updated_at': datetime.datetime.now().isoformat(),
            'error': str(e)
        }