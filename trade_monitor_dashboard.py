"""
Trade Monitor Dashboard

This dashboard displays:
1. Current setup messages
2. One chart card per active ticker
3. Real-time trade monitoring
"""
import json
import logging
import requests
import time
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Application configuration
API_BASE_URL = "http://localhost:5000"  # Flask API endpoint

# Set page configuration
st.set_page_config(
    page_title="A+ Trading Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def format_currency(value):
    """Format a number as USD currency"""
    return f"${value:,.2f}"

def format_percent(value):
    """Format a number as a percentage"""
    return f"{value:.2f}%"

def api_health_check():
    """Check if the API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_active_setups():
    """Get active trading setups from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/setups/active", timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching active setups: {e}")
        return []

def get_recent_messages():
    """Get recent Discord messages from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/discord/messages", timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching Discord messages: {e}")
        return []

def get_candle_data(ticker, timeframe="15Min", limit=100):
    """Get candle/price data for a ticker from the API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/market/candles/{ticker}",
            params={"timeframe": timeframe, "limit": limit},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching candle data for {ticker}: {e}")
        return []

def get_active_trades():
    """Get active trades from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/trades/active", timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching active trades: {e}")
        return []

def create_candlestick_chart(ticker, data=None, price_levels=None):
    """Create a candlestick chart for a given ticker symbol"""
    # Use sample data if no data is provided
    if not data:
        # Generate sample data for demonstration purposes
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        dates = pd.date_range(start=start_date, end=end_date, freq="15min")
        
        import numpy as np
        base_price = 100
        if ticker == "SPY":
            base_price = 586
        elif ticker == "AAPL":
            base_price = 182
        elif ticker == "NVDA":
            base_price = 920
        
        # Generate realistic price movements
        np.random.seed(42)  # For reproducibility
        close_prices = np.random.normal(0, 1, size=len(dates)).cumsum() * 0.5 + base_price
        
        data = []
        for i, date in enumerate(dates):
            # Create variation for open, high, low based on close
            close = close_prices[i]
            open_price = close * (1 + np.random.normal(0, 0.002))
            high = max(close, open_price) * (1 + abs(np.random.normal(0, 0.003)))
            low = min(close, open_price) * (1 - abs(np.random.normal(0, 0.003)))
            
            data.append({
                'timestamp': date.strftime('%Y-%m-%dT%H:%M:%S'),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': int(np.random.normal(1000000, 500000))
            })
    
    # Convert data to DataFrame
    if data:
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        
        # Create the figure
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, 
                          vertical_spacing=0.03, subplot_titles=[f"{ticker} Price Chart"], 
                          row_width=[1])
        
        # Add candlestick chart
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
        ))
        
        # Add price levels if provided
        if price_levels:
            for level_type, price in price_levels.items():
                if price:
                    color = "green"
                    if level_type == "resistance":
                        color = "red"
                    elif level_type == "support":
                        color = "green"
                    elif level_type == "target":
                        color = "blue"
                    elif level_type == "stop":
                        color = "purple"
                    
                    fig.add_hline(
                        y=price,
                        line_dash="dash",
                        line_color=color,
                        annotation_text=f"{level_type.capitalize()}: {price}",
                        annotation_position="right"
                    )
        
        # Update layout
        fig.update_layout(
            title=f"{ticker} - 15 Minute Chart",
            xaxis_title="Time",
            yaxis_title="Price",
            height=500,
            xaxis_rangeslider_visible=False,
            margin=dict(l=50, r=50, t=85, b=50),
        )
        
        return fig
    
    return None

def display_message_card(message):
    """Display a message card with clean formatting"""
    if not message:
        return
    
    st.subheader("Latest Trading Setup")
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**Date:** {message.get('datetime', 'N/A')}")
            st.markdown(f"**Message:**")
            st.markdown(f"```\n{message.get('raw_message', 'No message available')}\n```")
        
        with col2:
            st.markdown(f"**Signal Type:** {message.get('signal_type', 'N/A')}")
            st.markdown(f"**Bias:** {message.get('bias', 'N/A')}")
            st.markdown(f"**Confidence:** {message.get('confidence', 0)*100:.0f}%")
            primary_ticker = message.get('primary_ticker', 'N/A')
            st.markdown(f"**Primary Ticker:** {primary_ticker}")
            st.markdown(f"**Tickers:** {', '.join(message.get('tickers', []))}")

def display_ticker_chart_card(ticker, message):
    """Display a chart card for a specific ticker"""
    if not ticker or not message:
        return
    
    # Get ticker-specific data from the message
    ticker_data = {}
    if message.get('ticker_specific_data') and ticker in message['ticker_specific_data']:
        ticker_data = message['ticker_specific_data'][ticker]
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Price levels for this ticker
            price_levels = {
                "support": ticker_data.get('support_levels', []),
                "resistance": ticker_data.get('resistance_levels', []),
                "target": ticker_data.get('target_levels', []),
                "stop": ticker_data.get('stop_levels', [])
            }
            
            # Extract the first value from each list or use None
            parsed_price_levels = {}
            for k, v in price_levels.items():
                if v and isinstance(v, list) and len(v) > 0:
                    parsed_price_levels[k] = v[0] 
                else:
                    parsed_price_levels[k] = None
            
            # Create and display the chart
            fig = create_candlestick_chart(ticker, data=None, price_levels=parsed_price_levels)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Could not create chart for {ticker}")
        
        with col2:
            st.subheader(f"{ticker} Details")
            st.markdown(f"**Signal:** {ticker_data.get('signal_type', 'N/A')}")
            st.markdown(f"**Bias:** {ticker_data.get('bias', 'N/A')}")
            
            # Display price levels
            support_levels = ticker_data.get('support_levels', [])
            if support_levels and isinstance(support_levels, list) and len(support_levels) > 0:
                st.markdown(f"**Support:** {support_levels[0]}")
            else:
                st.markdown("**Support:** N/A")
                
            resistance_levels = ticker_data.get('resistance_levels', [])
            if resistance_levels and isinstance(resistance_levels, list) and len(resistance_levels) > 0:
                st.markdown(f"**Resistance:** {resistance_levels[0]}")
            else:
                st.markdown("**Resistance:** N/A")
                
            target_levels = ticker_data.get('target_levels', [])
            if target_levels and isinstance(target_levels, list) and len(target_levels) > 0:
                st.markdown(f"**Target:** {target_levels[0]}")
            else:
                st.markdown("**Target:** N/A")
                
            stop_levels = ticker_data.get('stop_levels', [])
            if stop_levels and isinstance(stop_levels, list) and len(stop_levels) > 0:
                st.markdown(f"**Stop:** {stop_levels[0]}")
            else:
                st.markdown("**Stop:** N/A")
            
            # Add trade status
            trade_status = "No active trade"
            st.markdown(f"**Status:** {trade_status}")

def display_trade_monitor():
    """Display the main trade monitoring dashboard"""
    st.title("A+ Trading Monitor")
    
    # Try to get setup data from our provider
    try:
        import setup_data_provider
        setup_message = setup_data_provider.get_latest_setup()
        
        if not setup_message:
            setup_data_provider.update_setup_from_discord()
            setup_message = setup_data_provider.get_latest_setup()
        
        if not setup_message:
            st.error("Could not retrieve trading setup data.")
            
            # Fallback to sample data from the provider
            setup_message = setup_data_provider.get_sample_setup()
    except Exception as e:
        st.error(f"Error retrieving setup data: {str(e)}")
        
        # If the API is available, try to get data from there
        if api_health_check():
            # Get active setups
            active_setups = get_active_setups()
            if active_setups:
                setup_message = active_setups[0]
            else:
                # Get recent Discord messages
                recent_messages = get_recent_messages()
                if recent_messages:
                    setup_message = recent_messages[0]
                else:
                    # Use fallback sample message
                    st.warning("No recent setup data available.")
                    from setup_data_provider import get_sample_setup
                    setup_message = get_sample_setup()
        else:
            st.error("API is not available. Please check the server status.")
            from setup_data_provider import get_sample_setup
            setup_message = get_sample_setup()
    
    # Display the latest setup message
    display_message_card(setup_message)
    
    # Display charts for each ticker
    st.header("Active Ticker Charts")
    st.markdown("---")
    
    # Get tickers from the sample message
    tickers = sample_message.get('tickers', [])
    
    # Skip ticker 'A' if it exists (likely not a real ticker in this context)
    tickers = [ticker for ticker in tickers if ticker != 'A']
    
    for ticker in tickers:
        display_ticker_chart_card(ticker, sample_message)
        st.markdown("---")
    
    # Get and display active trades
    active_trades = get_active_trades()
    if active_trades:
        st.header("Active Trades")
        # Check if active_trades is a dict or list
        if isinstance(active_trades, dict):
            # Handle dictionary format
            for trade_id, trade_data in active_trades.items():
                st.subheader(f"{trade_data.get('primary_ticker')} Trade")
                st.markdown(f"**Signal:** {trade_data.get('signal_type')}")
                st.markdown(f"**Status:** {trade_data.get('status')}")
                if 'trade_data' in trade_data:
                    st.markdown(f"**Entry Price:** {format_currency(trade_data['trade_data'].get('entry_price', 0))}")
                    st.markdown(f"**Current Price:** {format_currency(trade_data['trade_data'].get('current_price', 0))}")
                    st.markdown(f"**P/L:** {format_percent(trade_data['trade_data'].get('profit_loss', 0))}")
                st.markdown("---")
        elif isinstance(active_trades, list):
            # Handle list format
            for trade_data in active_trades:
                st.subheader(f"{trade_data.get('primary_ticker', 'Unknown')} Trade")
                st.markdown(f"**Signal:** {trade_data.get('signal_type', 'N/A')}")
                st.markdown(f"**Status:** {trade_data.get('status', 'Unknown')}")
                if 'trade_data' in trade_data:
                    st.markdown(f"**Entry Price:** {format_currency(trade_data['trade_data'].get('entry_price', 0))}")
                    st.markdown(f"**Current Price:** {format_currency(trade_data['trade_data'].get('current_price', 0))}")
                    st.markdown(f"**P/L:** {format_percent(trade_data['trade_data'].get('profit_loss', 0))}")
                st.markdown("---")

if __name__ == "__main__":
    display_trade_monitor()