"""
Setup Monitor View

This module provides a dashboard view for monitoring trade setups and market signals.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

# Import components
from ..components.chart_component import create_candlestick_chart, display_chart, create_multi_ticker_chart
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
def get_setup_data():
    """Get data for setup monitoring"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard/data/setups")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch setup data: {response.status_code}")
            return {}
    except Exception as e:
        st.error(f"Error fetching setup data: {str(e)}")
        return {}

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

def categorize_setups(setups):
    """Categorize setups by type"""
    categorized = {
        "breakout": [],
        "breakdown": [],
        "rejection": [],
        "bounce": [],
        "other": []
    }
    
    for setup in setups:
        category = setup.get('category', '').lower()
        if category in categorized:
            categorized[category].append(setup)
        else:
            categorized["other"].append(setup)
    
    return categorized

def render():
    """Render the setup monitor view"""
    # Get setup data
    setup_data = get_setup_data()
    
    if not setup_data:
        st.info("Setup data is not available. Please check your API connection.")
        return
    
    # Extract data components
    setups = setup_data.get('setups', [])
    signals = setup_data.get('signals', [])
    prices = setup_data.get('prices', {})
    tickers = setup_data.get('tickers', [])
    
    # Display summary metrics
    st.subheader("Setup Overview")
    
    # Create metrics for setups
    setup_metrics = [
        {
            'label': 'Active Setups',
            'value': len(setups)
        },
        {
            'label': 'Active Signals',
            'value': len(signals)
        },
        {
            'label': 'Tracked Tickers',
            'value': len(tickers)
        }
    ]
    
    create_metrics_row(setup_metrics)
    
    # Categorize setups
    categorized_setups = categorize_setups(setups)
    
    # Display setup tabs by category
    st.subheader("Setups by Category")
    
    category_tabs = st.tabs([
        f"Breakout ({len(categorized_setups['breakout'])})",
        f"Breakdown ({len(categorized_setups['breakdown'])})",
        f"Rejection ({len(categorized_setups['rejection'])})",
        f"Bounce ({len(categorized_setups['bounce'])})",
        f"Other ({len(categorized_setups['other'])})"
    ])
    
    categories = ["breakout", "breakdown", "rejection", "bounce", "other"]
    
    for i, tab in enumerate(category_tabs):
        with tab:
            category = categories[i]
            category_setups = categorized_setups[category]
            
            if category_setups:
                # Convert to DataFrame for display
                setups_df = pd.DataFrame(category_setups)
                
                # Format data
                formatting = {
                    'price': format_currency,
                    'trigger_price': format_currency,
                    'target_price': format_currency
                }
                
                create_data_table(setups_df, formatting=formatting)
                
                # Display charts for this category's tickers
                category_tickers = [setup.get('symbol') for setup in category_setups if 'symbol' in setup]
                
                if category_tickers:
                    st.subheader(f"{category.capitalize()} Setup Charts")
                    
                    # Get chart data for these tickers
                    ticker_data = {}
                    for ticker in category_tickers[:5]:  # Limit to 5 for performance
                        candle_data = get_candle_data(ticker)
                        if not candle_data.empty:
                            ticker_data[ticker] = candle_data
                    
                    # Create multi-ticker comparison chart
                    if ticker_data:
                        comparison_chart = create_multi_ticker_chart(
                            ticker_data,
                            chart_title=f"{category.capitalize()} Setups Comparison"
                        )
                        st.plotly_chart(comparison_chart, use_container_width=True)
                    
                    # Display individual ticker charts
                    for ticker in category_tickers[:3]:  # Limit to 3 for performance
                        st.subheader(f"{ticker} Chart")
                        candle_data = get_candle_data(ticker)
                        
                        # Get signals for this ticker
                        ticker_signals = [s for s in signals if s.get('symbol') == ticker]
                        
                        if not candle_data.empty:
                            chart_args = {
                                'symbol': ticker,
                                'data': candle_data,
                                'signals': ticker_signals
                            }
                            display_chart(create_candlestick_chart, chart_args, key=f"chart_{category}_{ticker}")
                        else:
                            st.info(f"No price data available for {ticker}")
            else:
                st.info(f"No {category} setups available")
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")