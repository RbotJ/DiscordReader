"""
Dashboard Data Service

This module provides data access services for the dashboard feature.
It centralizes data retrieval logic for all dashboard views.
"""

import logging
import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from common.db import execute_query

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

def get_system_status() -> Dict[str, Any]:
    """
    Get system status data showing operational telemetry.
    
    Returns:
        Dictionary containing:
        - recent_discord_messages: 5 most recent raw Discord messages
        - todays_messages: All messages for current trading day
        - todays_setups: Parsed setups for current trading day
        - tickers_summary: Parsed tickers with trade types and watch levels
    """
    try:
        today = datetime.datetime.now().date()
        
        # Get 5 most recent Discord messages from events table (fixed column name)
        recent_messages_query = """
            SELECT 
                created_at,
                event_type,
                data
            FROM events 
            WHERE channel LIKE %s 
            ORDER BY created_at DESC 
            LIMIT 5
        """
        recent_messages = execute_query(recent_messages_query, ['discord%']) or []
        
        # Get all messages for today
        todays_messages_query = """
            SELECT 
                created_at,
                event_type,
                data
            FROM events 
            WHERE channel LIKE %s 
            AND DATE(created_at) = %s
            ORDER BY created_at DESC
        """
        todays_messages = execute_query(todays_messages_query, ['discord%', today]) or []
        
        # Get parsed setups for today from existing trade_setups table
        todays_setups_query = """
            SELECT 
                id,
                ticker,
                setup_type,
                watch_levels,
                trading_day,
                created_at,
                active
            FROM trade_setups 
            WHERE DATE(created_at) = %s
            ORDER BY created_at DESC
        """
        todays_setups = execute_query(todays_setups_query, [today]) or []
        
        # Get ticker summaries with trade types and watch levels
        ticker_summary_query = """
            SELECT 
                ticker,
                setup_type,
                watch_levels,
                COUNT(*) as setup_count,
                MAX(created_at) as latest_setup
            FROM trade_setups 
            WHERE DATE(created_at) = %s
            AND active = true
            GROUP BY ticker, setup_type, watch_levels
            ORDER BY latest_setup DESC
        """
        tickers_summary = execute_query(ticker_summary_query, [today]) or []
        
        # Format the data for better readability
        formatted_recent_messages = []
        for msg in recent_messages:
            try:
                data_field = msg.get('data', {})
                content = ''
                if isinstance(data_field, dict):
                    content = data_field.get('content', str(data_field))[:100]
                else:
                    content = str(data_field)[:100]
                
                formatted_recent_messages.append({
                    'timestamp': msg.get('created_at'),
                    'type': msg.get('event_type'),
                    'content': content
                })
            except Exception as e:
                logger.warning(f"Error formatting message: {e}")
                continue
        
        formatted_todays_setups = []
        for setup in todays_setups:
            formatted_todays_setups.append({
                'id': setup.get('id'),
                'ticker': setup.get('ticker'),
                'setup_type': setup.get('setup_type'),
                'watch_levels': setup.get('watch_levels'),
                'trading_day': setup.get('trading_day'),
                'active': setup.get('active'),
                'created_at': setup.get('created_at')
            })
        
        formatted_tickers_summary = []
        for ticker in tickers_summary:
            # Extract first watch level from JSONB if available
            watch_levels = ticker.get('watch_levels', {})
            first_level = None
            if isinstance(watch_levels, dict) and watch_levels:
                first_level = next(iter(watch_levels.values()), None)
            
            formatted_tickers_summary.append({
                'ticker': ticker.get('ticker'),
                'setup_type': ticker.get('setup_type'),
                'direction': 'mixed',  # Default since old table doesn't have this
                'watch_level': first_level,
                'confidence': 0.5,  # Default since old table doesn't have this
                'setup_count': ticker.get('setup_count'),
                'latest_setup': ticker.get('latest_setup')
            })
        
        return {
            'recent_discord_messages': formatted_recent_messages,
            'todays_messages_count': len(todays_messages),
            'todays_setups': formatted_todays_setups,
            'tickers_summary': formatted_tickers_summary,
            'date': today.isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            'recent_discord_messages': [],
            'todays_messages_count': 0,
            'todays_setups': [],
            'tickers_summary': [],
            'date': datetime.datetime.now().date().isoformat(),
            'updated_at': datetime.datetime.now().isoformat(),
            'error': str(e)
        }