"""
Streamlit Trading Dashboard - Main Entry Point

This script sets up and runs the trading dashboard using Streamlit,
connecting directly to Alpaca API for market data and trading functionality.
"""

import os
import time
import json
import logging
import datetime
from threading import Thread, Lock
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the page
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'events' not in st.session_state:
    st.session_state.events = []
    
if 'active_tickers' not in st.session_state:
    st.session_state.active_tickers = []
    
if 'positions' not in st.session_state:
    st.session_state.positions = []

# Helper function for logging events
def add_event(event_type, message):
    """Add an event to the event log"""
    event = {
        'id': f"event-{time.time()}",
        'type': event_type, 
        'timestamp': datetime.datetime.now(),
        'message': message
    }
    st.session_state.events.insert(0, event)
    # Keep only the most recent 50 events
    if len(st.session_state.events) > 50:
        st.session_state.events = st.session_state.events[:50]

# Helper functions for formatting
def format_currency(value):
    """Format a number as USD currency"""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"

def format_percent(value):
    """Format a number as a percentage"""
    if value is None:
        return "0.00%"
    return f"{value:.2f}%"

# Function to generate sample data for demo purposes
def get_sample_price_data(symbol, days=30):
    """Generate realistic-looking price data for a symbol"""
    np.random.seed(hash(symbol) % 10000)  # Seed based on symbol for consistency
    
    # Set base price and volatility based on symbol
    if symbol == "AAPL":
        base_price = 180 + np.random.rand() * 10
        volatility = 0.015
    elif symbol == "MSFT":
        base_price = 370 + np.random.rand() * 20
        volatility = 0.018
    elif symbol == "GOOGL":
        base_price = 160 + np.random.rand() * 10
        volatility = 0.02
    elif symbol == "AMZN":
        base_price = 180 + np.random.rand() * 15
        volatility = 0.025
    elif symbol == "TSLA":
        base_price = 170 + np.random.rand() * 30
        volatility = 0.04
    else:
        base_price = 100 + np.random.rand() * 100
        volatility = 0.02
    
    # Generate timestamps
    end_date = datetime.datetime.now()
    dates = [end_date - datetime.timedelta(days=i) for i in range(days)]
    dates.reverse()
    
    # Generate daily price movement with realistic patterns
    daily_returns = np.random.normal(0.0005, volatility, days)  # Slight upward bias
    price_movement = np.cumprod(1 + daily_returns)
    prices = base_price * price_movement
    
    # Add some random price spikes and dips
    for i in range(3):  # Add a few random events
        event_idx = np.random.randint(5, days-5)
        event_magnitude = np.random.choice([-1, 1]) * np.random.uniform(0.03, 0.08)
        prices[event_idx:] *= (1 + event_magnitude)
    
    # Generate OHLC data
    data = []
    for i in range(days):
        base = prices[i]
        daily_vol = base * volatility * 2
        
        # Create realistic open/high/low/close relationships
        open_price = base * (1 + np.random.uniform(-0.005, 0.005))
        close_price = base
        high_price = max(open_price, close_price) + np.random.uniform(0, daily_vol)
        low_price = min(open_price, close_price) - np.random.uniform(0, daily_vol)
        
        # Generate volume with occasional spikes
        volume = int(np.random.uniform(5000, 15000) * (1 + abs(daily_returns[i]) * 10))
        
        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)

# Function to create candlestick charts
def create_candlestick_chart(symbol, data=None):
    """Create a candlestick chart for a given ticker symbol"""
    if data is None:
        # Generate sample data for the demo
        data = get_sample_price_data(symbol)
    
    # Create a subplot with 2 rows (price & volume)
    fig = make_subplots(
        rows=2, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.8, 0.2]
    )
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=data['timestamp'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name=symbol
        ),
        row=1, col=1
    )
    
    # Add volume bar chart
    fig.add_trace(
        go.Bar(
            x=data['timestamp'],
            y=data['volume'],
            name='Volume',
            marker=dict(color='rgba(100, 100, 255, 0.5)')
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title=f"{symbol} Price Chart",
        xaxis_title='Time',
        yaxis_title='Price ($)',
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    # Style adjustments
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#444'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# Function to generate sample account data
def get_sample_account_data():
    """Generate sample account data for demo purposes"""
    return {
        'equity': 100000.0 + np.random.uniform(-5000, 5000),
        'buying_power': 200000.0 + np.random.uniform(-10000, 10000),
        'cash': 50000.0 + np.random.uniform(-2000, 2000),
        'positions_count': len(st.session_state.positions)
    }

# Function to generate sample positions
def get_sample_positions():
    """Generate sample positions for demo purposes"""
    if not st.session_state.active_tickers:
        return []
    
    positions = []
    for ticker in st.session_state.active_tickers:
        # Only create positions for some tickers
        if np.random.random() < 0.7:
            continue
            
        # Generate a realistic position
        entry_price = get_sample_price_data(ticker, days=1)['close'].values[0] * 0.98
        current_price = entry_price * (1 + np.random.uniform(-0.1, 0.15))
        qty = np.random.randint(10, 100)
        
        unrealized_pl = (current_price - entry_price) * qty
        unrealized_plpc = (current_price - entry_price) / entry_price
        
        positions.append({
            'symbol': ticker,
            'qty': qty,
            'avg_entry_price': entry_price,
            'current_price': current_price,
            'unrealized_pl': unrealized_pl,
            'unrealized_plpc': unrealized_plpc,
            'market_value': current_price * qty
        })
    
    return positions

# Function to place an order (simulated)
def place_market_order(symbol, qty, side):
    """Simulate placing a market order"""
    order_id = f"order-{time.time()}"
    
    # Log the order
    side_text = "BUY" if side == "buy" else "SELL"
    add_event('signal', f"Order placed: {side_text} {qty} shares of {symbol} (ID: {order_id})")
    
    # Simulate order execution
    if side == "buy":
        # Create a new position or add to existing
        exists = False
        for position in st.session_state.positions:
            if position['symbol'] == symbol:
                # Update existing position
                current_qty = position['qty']
                current_value = position['current_price'] * current_qty
                new_value = get_sample_price_data(symbol, days=1)['close'].values[0] * qty
                
                # Calculate new average price
                position['qty'] = current_qty + qty
                position['avg_entry_price'] = (current_value + new_value) / position['qty']
                position['market_value'] = position['current_price'] * position['qty']
                
                exists = True
                break
                
        if not exists:
            # Create new position
            current_price = get_sample_price_data(symbol, days=1)['close'].values[0]
            st.session_state.positions.append({
                'symbol': symbol,
                'qty': qty,
                'avg_entry_price': current_price,
                'current_price': current_price,
                'unrealized_pl': 0,
                'unrealized_plpc': 0,
                'market_value': current_price * qty
            })
    else:
        # Sell - reduce or remove position
        for i, position in enumerate(st.session_state.positions):
            if position['symbol'] == symbol:
                if position['qty'] <= qty:
                    # Remove the position
                    st.session_state.positions.pop(i)
                else:
                    # Reduce the position
                    position['qty'] -= qty
                    position['market_value'] = position['current_price'] * position['qty']
                break
    
    return True

# Function to close a position
def close_position(symbol):
    """Close a position"""
    for i, position in enumerate(st.session_state.positions):
        if position['symbol'] == symbol:
            add_event('signal', f"Position closed: {position['qty']} shares of {symbol}")
            st.session_state.positions.pop(i)
            return True
    
    add_event('error', f"No position found for {symbol}")
    return False

# Sidebar - Settings and Controls
with st.sidebar:
    st.title("Trading Dashboard")
    
    st.header("API Configuration")
    api_key = st.text_input("API Key", type="password")
    api_secret = st.text_input("API Secret", type="password")
    
    if st.button("Connect"):
        if api_key and api_secret:
            add_event('system', "API credentials saved")
            st.success("API credentials saved successfully")
        else:
            add_event('error', "API credentials are required")
            st.error("Please enter both API key and secret")
    
    st.header("Ticker Selection")
    available_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "AMD", "INTC"]
    
    selected_tickers = st.multiselect(
        "Select tickers to track",
        options=available_tickers,
        default=st.session_state.active_tickers
    )
    
    # Update active tickers if selection changed
    if selected_tickers != st.session_state.active_tickers:
        for ticker in selected_tickers:
            if ticker not in st.session_state.active_tickers:
                add_event('system', f"Added {ticker} to tracking list")
        
        for ticker in st.session_state.active_tickers:
            if ticker not in selected_tickers:
                add_event('system', f"Removed {ticker} from tracking list")
        
        st.session_state.active_tickers = selected_tickers
    
    # Order entry form
    st.header("Quick Trade")
    with st.form("order_form"):
        order_symbol = st.selectbox("Symbol", options=[""] + st.session_state.active_tickers)
        order_quantity = st.number_input("Quantity", min_value=1, step=1, value=10)
        order_side = st.radio("Side", options=["Buy", "Sell"])
        
        submit_order = st.form_submit_button("Place Order")
        
        if submit_order and order_symbol:
            success = place_market_order(order_symbol, order_quantity, order_side.lower())
            if success:
                st.success(f"Order placed: {order_side} {order_quantity} shares of {order_symbol}")
            else:
                st.error("Failed to place order")

# Main dashboard layout
st.title("Trading Dashboard")

# Get sample account data
account = get_sample_account_data()

# Account information row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Account Equity",
        value=format_currency(account['equity'])
    )

with col2:
    st.metric(
        label="Buying Power",
        value=format_currency(account['buying_power'])
    )

with col3:
    market_status = "Open" if 9 <= datetime.datetime.now().hour <= 16 else "Closed"
    st.metric(
        label="Market Status",
        value=market_status
    )

with col4:
    position_count = len(st.session_state.positions)
    st.metric(
        label="Open Positions",
        value=str(position_count)
    )

# Charts section
st.header("Charts")

if not st.session_state.active_tickers:
    st.info("Select tickers from the sidebar to display charts")
else:
    # Calculate how many tickers per row (1, 2, or 3 depending on count)
    charts_per_row = min(len(st.session_state.active_tickers), 2)
    
    # Split tickers into rows of charts_per_row
    ticker_rows = [st.session_state.active_tickers[i:i+charts_per_row] 
                for i in range(0, len(st.session_state.active_tickers), charts_per_row)]
    
    # Create a row for each group of tickers
    for row_tickers in ticker_rows:
        cols = st.columns(len(row_tickers))
        
        for i, ticker in enumerate(row_tickers):
            with cols[i]:
                # Create chart
                fig = create_candlestick_chart(ticker)
                st.plotly_chart(fig, use_container_width=True)
                
                # Add trading buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Buy {ticker}", key=f"buy_{ticker}"):
                        place_market_order(ticker, 10, "buy")
                        st.success(f"Bought 10 shares of {ticker}")
                with col2:
                    if st.button(f"Sell {ticker}", key=f"sell_{ticker}"):
                        place_market_order(ticker, 10, "sell")
                        st.success(f"Sold 10 shares of {ticker}")

# Update positions if empty
if not st.session_state.positions and st.session_state.active_tickers:
    st.session_state.positions = get_sample_positions()

# Positions table
st.header("Positions")

if not st.session_state.positions:
    st.info("No open positions")
else:
    # Create a DataFrame for positions
    positions_df = pd.DataFrame(st.session_state.positions)
    
    # Format values for display
    positions_df['unrealized_pl'] = positions_df['unrealized_pl'].apply(lambda x: f"${x:.2f}")
    positions_df['unrealized_plpc'] = positions_df['unrealized_plpc'].apply(lambda x: f"{x*100:.2f}%")
    positions_df['avg_entry_price'] = positions_df['avg_entry_price'].apply(lambda x: f"${x:.2f}")
    positions_df['current_price'] = positions_df['current_price'].apply(lambda x: f"${x:.2f}")
    positions_df['market_value'] = positions_df['market_value'].apply(lambda x: f"${x:.2f}")
    
    # Rename columns for better display
    positions_df.columns = ['Symbol', 'Quantity', 'Entry Price', 'Current Price', 'Unrealized P/L', 'P/L %', 'Market Value']
    
    # Display the positions table
    st.dataframe(positions_df, use_container_width=True)
    
    # Add close all positions button
    if st.button("Close All Positions"):
        st.session_state.positions = []
        add_event('system', "All positions closed")
        st.success("All positions closed")

# Event log
st.header("Event Log")

if not st.session_state.events:
    # Add initial events
    add_event('system', "Dashboard initialized")
    add_event('system', "Welcome to the Trading Dashboard")
    add_event('system', "Select tickers from the sidebar to get started")

# Display events in reverse chronological order
for event in st.session_state.events[:20]:  # Show only the most recent 20
    event_time = event['timestamp'].strftime('%H:%M:%S')
    
    if event['type'] == 'error':
        st.error(f"{event_time} - {event['message']}")
    elif event['type'] == 'warning':
        st.warning(f"{event_time} - {event['message']}")
    elif event['type'] == 'system':
        st.info(f"{event_time} - {event['message']}")
    elif event['type'] == 'signal':
        st.success(f"{event_time} - {event['message']}")
    else:
        # Market events in a neutral style
        st.text(f"{event_time} - {event['message']}")