"""
Main Dashboard View

This module provides the main dashboard view showing an overview of the trading system.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime
import logging
from typing import Dict, Any, List

# Import components
from ..components.chart_component import create_candlestick_chart, display_chart
from ..components.table_component import create_data_table, create_metrics_row

# Setup logging
logger = logging.getLogger(__name__)

# API base URL - Flask backend
API_BASE_URL = "http://localhost:5000/api"

# Helper functions for formatting
def format_currency(value):
    """Format a number as USD currency"""
    if value is None:
        return "$0.00"
    return f"${float(value):,.2f}"

def format_percent(value):
    """Format a number as a percentage"""
    if value is None:
        return "0.00%"
    return f"{float(value):.2f}%"

# Data retrieval functions
def get_summary_data():
    """Get summary data for the main dashboard"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard/data/summary")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch summary data: {response.status_code}")
            return {}
    except Exception as e:
        st.error(f"Error fetching summary data: {str(e)}")
        return {}

def get_active_positions():
    """Get active positions data"""
    try:
        response = requests.get(f"{API_BASE_URL}/execution/positions")
        if response.status_code == 200:
            data = response.json()
            if 'positions' in data:
                return data['positions']
            return []
        else:
            st.error(f"Failed to fetch positions: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching positions: {str(e)}")
        return []

def get_available_tickers():
    """Get available tickers for tracking"""
    try:
        response = requests.get(f"{API_BASE_URL}/tickers")
        if response.status_code == 200:
            return response.json().get('tickers', [])
        else:
            st.error(f"Failed to fetch tickers: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching tickers: {str(e)}")
        return []

def get_recent_trades():
    """Get recent trades data"""
    try:
        response = requests.get(f"{API_BASE_URL}/execution/trades")
        if response.status_code == 200:
            data = response.json()
            if 'trades' in data:
                return data['trades']
            return []
        else:
            st.error(f"Failed to fetch recent trades: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching recent trades: {str(e)}")
        return []

def get_candle_data(ticker, timeframe="1Day", limit=100):
    """Get candle data for a specific ticker"""
    try:
        response = requests.get(f"{API_BASE_URL}/market/candles/{ticker}?timeframe={timeframe}&limit={limit}")
        if response.status_code == 200:
            data = response.json()
            if 'candles' in data:
                # Convert to DataFrame with proper column names
                df = pd.DataFrame(data['candles'])
                if len(df) > 0:
                    # Ensure proper datetime format for timestamp
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    return df
                return pd.DataFrame()
            return pd.DataFrame()
        else:
            st.error(f"Failed to fetch candle data for {ticker}: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching candle data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_signals(ticker):
    """Get trading signals for a ticker"""
    try:
        response = requests.get(f"{API_BASE_URL}/strategy/signals/{ticker}")
        if response.status_code == 200:
            data = response.json()
            if 'signals' in data:
                return data['signals']
            return []
        else:
            st.error(f"Failed to fetch signals for {ticker}: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching signals for {ticker}: {str(e)}")
        return []

def render():
    """Render the main dashboard view"""
    # Create dashboard layout with multiple sections
    
    # Get summary data
    summary_data = get_summary_data()
    
    # Display account and market metrics
    if summary_data and 'account' in summary_data:
        account = summary_data.get('account', {})
        market = summary_data.get('market', {})
        
        # Account metrics
        account_metrics = [
            {
                'label': 'Portfolio Value',
                'value': format_currency(account.get('portfolio_value')),
                'delta': format_percent(account.get('portfolio_change_percent'))
            },
            {
                'label': 'Cash Balance',
                'value': format_currency(account.get('cash')),
            },
            {
                'label': 'Buying Power',
                'value': format_currency(account.get('buying_power')),
            }
        ]
        
        # Market metrics
        market_metrics = [
            {
                'label': 'Market Status',
                'value': market.get('status', 'Unknown'),
            },
            {
                'label': 'Next Market Open',
                'value': market.get('next_open', 'Unknown'),
            },
            {
                'label': 'Active Setups',
                'value': summary_data.get('active_setups_count', 0),
            }
        ]
        
        # Display metrics in two rows
        st.subheader("Account Overview")
        create_metrics_row(account_metrics)
        
        st.subheader("Market Status")
        create_metrics_row(market_metrics)
    else:
        st.info("Account and market data not available. Please check your API connection.")
    
    # Create two column layout for positions and charts
    col1, col2 = st.columns([1, 2])
    
    # Display active positions in first column
    with col1:
        st.subheader("Active Positions")
        positions = get_active_positions()
        
        if positions:
            positions_df = pd.DataFrame(positions)
            
            # Format the positions data
            formatting = {
                'current_price': format_currency,
                'avg_entry_price': format_currency,
                'market_value': format_currency,
                'unrealized_pl': format_currency,
                'unrealized_plpc': format_percent,
            }
            
            create_data_table(positions_df, formatting=formatting)
        else:
            st.info("No active positions")
        
        # Display recent trades below positions
        st.subheader("Recent Trades")
        trades = get_recent_trades()
        
        if trades:
            trades_df = pd.DataFrame(trades)
            
            # Format the trades data
            formatting = {
                'price': format_currency,
                'filled_qty': lambda x: f"{x} shares",
                'filled_avg_price': format_currency,
                'profit_loss': format_currency,
            }
            
            create_data_table(trades_df, formatting=formatting)
        else:
            st.info("No recent trades")
    
    # Display charts in second column
    with col2:
        st.subheader("Latest Price Charts")
        
        # Get available tickers
        tickers = get_available_tickers()
        
        if not tickers:
            tickers = ["SPY", "QQQ", "AAPL"]  # Default tickers if none available
        
        # Create tabs for different tickers
        ticker_tabs = st.tabs(tickers[:5])  # Limit to 5 tickers for performance
        
        for i, tab in enumerate(ticker_tabs):
            if i < len(tickers):
                ticker = tickers[i]
                with tab:
                    # Get data for this ticker
                    candle_data = get_candle_data(ticker)
                    signals = get_signals(ticker)
                    
                    # Display chart
                    if not candle_data.empty:
                        chart_args = {
                            'symbol': ticker,
                            'data': candle_data,
                            'signals': signals
                        }
                        display_chart(create_candlestick_chart, chart_args, key=f"chart_{ticker}")
                    else:
                        st.info(f"No price data available for {ticker}")
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")