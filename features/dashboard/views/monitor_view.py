"""
Monitoring Dashboard View

This module provides a dashboard for monitoring trade setups, prices, and signals.
Integrated from the original monitoring_dashboard.py.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional, Tuple

# Import components
from ..components.chart_component import create_candlestick_chart, display_chart
from ..components.table_component import create_data_table, create_metrics_row

# Setup logging
logger = logging.getLogger(__name__)

# API base URL - Flask backend
API_BASE_URL = "http://localhost:5000/api"

# Constants
DEFAULT_TIMEFRAMES = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
DEFAULT_PERIOD = 20  # Number of candles to show by default

# Helper functions for formatting
def format_currency(value):
    """Format a value as USD currency"""
    if value is None:
        return "N/A"
    return f"${float(value):,.2f}"

def format_percent(value):
    """Format a value as a percentage"""
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"

# Data retrieval functions
def fetch_api_data(endpoint, params=None):
    """Fetch data from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        st.error(f"Error fetching data from API: {e}")
        return None
    except ValueError as e:
        logger.error(f"JSON parsing error: {e}")
        st.error(f"Error parsing API response: {e}")
        return None

def fetch_tickers():
    """Fetch available tickers from the API"""
    data = fetch_api_data("tickers")
    if data and 'tickers' in data:
        return data['tickers']
    return []

def fetch_candle_data(ticker, timeframe="1Day", limit=100):
    """Fetch candle data for a ticker"""
    data = fetch_api_data(f"market/candles/{ticker}", {
        'timeframe': timeframe,
        'limit': limit
    })
    
    if data and 'candles' in data:
        df = pd.DataFrame(data['candles'])
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    return pd.DataFrame()

def fetch_signals(ticker):
    """Fetch trading signals for a ticker"""
    data = fetch_api_data(f"strategy/signals/{ticker}")
    if data and 'signals' in data:
        return data['signals']
    return []

def create_candlestick_chart_with_signals(ticker, candles, signals=None):
    """Create a candlestick chart with signals"""
    if candles.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"{ticker} - No Data Available",
            height=400
        )
        return fig
    
    # Create the figure
    fig = go.Figure()
    
    # Add candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=candles['timestamp'],
            open=candles['open'],
            high=candles['high'],
            low=candles['low'],
            close=candles['close'],
            name=ticker
        )
    )
    
    # Add volume as a bar chart on the same axis
    if 'volume' in candles.columns:
        # Scale volume to fit on the same chart
        max_price = candles['high'].max()
        volume_scale = max_price / candles['volume'].max() if candles['volume'].max() > 0 else 1
        scaled_volume = candles['volume'] * volume_scale * 0.2
        
        fig.add_trace(
            go.Bar(
                x=candles['timestamp'],
                y=scaled_volume,
                name='Volume',
                marker_color='rgba(0, 0, 255, 0.3)',
                opacity=0.3
            )
        )
    
    # Add signals if provided
    if signals:
        for i, signal in enumerate(signals):
            if 'trigger' in signal and 'price' in signal['trigger']:
                # Add horizontal line at trigger price
                fig.add_hline(
                    y=signal['trigger']['price'],
                    line_width=1,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"{signal.get('category', 'Signal')}"
                )
                
                # Add target lines if they exist
                if 'targets' in signal:
                    for j, target in enumerate(signal['targets']):
                        if 'price' in target:
                            fig.add_hline(
                                y=target['price'],
                                line_width=1,
                                line_dash="dot",
                                line_color="green",
                                annotation_text=f"Target {j+1}"
                            )
    
    # Update the layout
    fig.update_layout(
        title=f"{ticker} Price Chart",
        height=500,
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )
    
    return fig

def render():
    """Render the monitoring dashboard view"""
    st.title("Trade Setup Monitor")
    
    # Sidebar for controls
    st.sidebar.header("Controls")
    
    # Fetch available tickers
    available_tickers = fetch_tickers()
    if not available_tickers:
        available_tickers = ["SPY", "AAPL", "MSFT", "GOOGL", "AMZN"]  # Default tickers if API fails
    
    # Ticker selection
    selected_ticker = st.sidebar.selectbox(
        "Select Ticker",
        options=available_tickers,
        index=0
    )
    
    # Timeframe selection
    selected_timeframe = st.sidebar.selectbox(
        "Select Timeframe",
        options=DEFAULT_TIMEFRAMES,
        index=DEFAULT_TIMEFRAMES.index("1Day")
    )
    
    # Number of candles to display
    candle_count = st.sidebar.slider(
        "Number of Candles",
        min_value=10,
        max_value=200,
        value=DEFAULT_PERIOD
    )
    
    # Fetch data for the selected ticker
    candle_data = fetch_candle_data(selected_ticker, selected_timeframe, candle_count)
    signals = fetch_signals(selected_ticker)
    
    # Create metrics for the selected ticker
    if not candle_data.empty:
        latest_price = candle_data['close'].iloc[-1]
        prev_price = candle_data['close'].iloc[-2] if len(candle_data) > 1 else candle_data['open'].iloc[-1]
        price_change = latest_price - prev_price
        price_change_percent = (price_change / prev_price) * 100 if prev_price > 0 else 0
        
        # Display price metrics
        price_metrics = [
            {
                'label': f"{selected_ticker} Price",
                'value': format_currency(latest_price),
                'delta': format_percent(price_change_percent)
            },
            {
                'label': 'Change',
                'value': format_currency(price_change),
            },
            {
                'label': 'Volume',
                'value': f"{int(candle_data['volume'].iloc[-1]):,}" if 'volume' in candle_data.columns else "N/A",
            }
        ]
        
        create_metrics_row(price_metrics)
    
    # Create tabs for different views
    chart_tab, signals_tab, data_tab = st.tabs(["Chart", "Signals", "Data"])
    
    with chart_tab:
        if not candle_data.empty:
            # Create chart with signals
            fig = create_candlestick_chart_with_signals(selected_ticker, candle_data, signals)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No price data available for {selected_ticker}")
    
    with signals_tab:
        st.subheader("Trading Signals")
        if signals:
            signals_df = pd.DataFrame(signals)
            
            # Format signals data for display
            for signal in signals:
                if 'trigger' in signal:
                    signal['trigger_price'] = signal['trigger'].get('price', 'N/A')
                if 'targets' in signal and signal['targets']:
                    signal['target_1'] = signal['targets'][0].get('price', 'N/A') if len(signal['targets']) > 0 else 'N/A'
                    signal['target_2'] = signal['targets'][1].get('price', 'N/A') if len(signal['targets']) > 1 else 'N/A'
            
            # Create a cleaner DataFrame for display
            display_signals = []
            for signal in signals:
                display_signals.append({
                    'Category': signal.get('category', 'N/A'),
                    'Trigger Price': signal.get('trigger_price', 'N/A'),
                    'Target 1': signal.get('target_1', 'N/A'),
                    'Target 2': signal.get('target_2', 'N/A'),
                    'Status': signal.get('status', 'N/A')
                })
            
            display_df = pd.DataFrame(display_signals)
            
            # Format the data
            formatting = {
                'Trigger Price': format_currency,
                'Target 1': format_currency,
                'Target 2': format_currency
            }
            
            create_data_table(display_df, formatting=formatting)
        else:
            st.info(f"No signals available for {selected_ticker}")
    
    with data_tab:
        st.subheader("Price Data")
        if not candle_data.empty:
            # Format the candle data for display
            display_candles = candle_data.copy()
            if 'timestamp' in display_candles.columns:
                display_candles['Date'] = display_candles['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            
            # Select and rename columns for display
            selected_columns = ['Date', 'open', 'high', 'low', 'close', 'volume'] if 'volume' in display_candles.columns else ['Date', 'open', 'high', 'low', 'close']
            display_candles = display_candles[selected_columns]
            
            # Rename columns for better display
            column_rename = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            display_candles = display_candles.rename(columns=column_rename)
            
            # Format the data
            formatting = {
                'Open': format_currency,
                'High': format_currency,
                'Low': format_currency,
                'Close': format_currency,
                'Volume': lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A"
            }
            
            create_data_table(display_candles, formatting=formatting)
        else:
            st.info(f"No price data available for {selected_ticker}")
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")