"""
Trade Monitor View

This module provides a dashboard view for monitoring trades and positions.
Integrated from the original trade_monitor_dashboard.py.
"""

import streamlit as st
import pandas as pd
import requests
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import components
from ..components.chart_component import create_candlestick_chart, display_chart
from ..components.table_component import create_data_table, create_metrics_row, create_expandable_table

# Setup logging
logger = logging.getLogger(__name__)

# API base URL - Flask backend
API_BASE_URL = "http://localhost:5000/api"

# Helper functions for formatting
def format_currency(value):
    """Format a number as USD currency"""
    if value is None:
        return "N/A"
    return f"${float(value):,.2f}"

def format_percent(value):
    """Format a number as a percentage"""
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"

def format_quantity(value):
    """Format a quantity value"""
    if value is None:
        return "N/A"
    return f"{int(value):,}"

# Data retrieval functions
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

def get_open_orders():
    """Get open orders data"""
    try:
        response = requests.get(f"{API_BASE_URL}/execution/orders")
        if response.status_code == 200:
            data = response.json()
            if 'orders' in data:
                return data['orders']
            return []
        else:
            st.error(f"Failed to fetch orders: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching orders: {str(e)}")
        return []

def get_trade_history():
    """Get trade execution history"""
    try:
        response = requests.get(f"{API_BASE_URL}/execution/history")
        if response.status_code == 200:
            data = response.json()
            if 'trades' in data:
                return data['trades']
            return []
        else:
            st.error(f"Failed to fetch trade history: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching trade history: {str(e)}")
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

def get_account_data():
    """Get account data from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/account")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch account data: {response.status_code}")
            return {}
    except Exception as e:
        st.error(f"Error fetching account data: {str(e)}")
        return {}

def place_order(data):
    """Place an order via the API"""
    try:
        response = requests.post(f"{API_BASE_URL}/execution/order", json=data)
        if response.status_code == 200:
            st.success("Order placed successfully!")
            return response.json()
        else:
            st.error(f"Failed to place order: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error placing order: {str(e)}")
        return None

def close_position(symbol, percentage=1.0):
    """Close a position via the API"""
    try:
        payload = {'percentage': percentage}
        response = requests.post(f"{API_BASE_URL}/execution/close/{symbol}", json=payload)
        if response.status_code == 200:
            st.success(f"Position {symbol} closed successfully!")
            return response.json()
        else:
            st.error(f"Failed to close position: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error closing position: {str(e)}")
        return None

def render():
    """Render the trade monitor view"""
    st.title("Trade Monitor")
    
    # Create layout with multiple sections
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Account summary
        st.subheader("Account Summary")
        account_data = get_account_data()
        
        if account_data:
            # Create metrics for account
            account_metrics = [
                {
                    'label': 'Portfolio Value',
                    'value': format_currency(account_data.get('portfolio_value')),
                    'delta': format_percent(account_data.get('portfolio_change_percent'))
                },
                {
                    'label': 'Cash Balance',
                    'value': format_currency(account_data.get('cash')),
                },
                {
                    'label': 'Buying Power',
                    'value': format_currency(account_data.get('buying_power')),
                }
            ]
            
            create_metrics_row(account_metrics)
        else:
            st.info("Account data not available")
        
        # Active positions
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
                'qty': format_quantity
            }
            
            create_data_table(positions_df, formatting=formatting)
            
            # Add position management actions
            st.subheader("Position Management")
            
            # Create a form for closing positions
            with st.form("close_position_form"):
                selected_position = st.selectbox(
                    "Select Position to Close",
                    options=[p.get('symbol') for p in positions if 'symbol' in p],
                    key="position_to_close"
                )
                
                close_percentage = st.slider(
                    "Percentage to Close",
                    min_value=0.1,
                    max_value=1.0,
                    value=1.0,
                    step=0.1,
                    format="%.1f",
                    key="close_percentage"
                )
                
                close_button = st.form_submit_button("Close Position")
                
                if close_button and selected_position:
                    result = close_position(selected_position, close_percentage)
                    if result:
                        st.experimental_rerun()
        else:
            st.info("No active positions")
    
    with col2:
        # Open orders
        st.subheader("Open Orders")
        orders = get_open_orders()
        
        if orders:
            orders_df = pd.DataFrame(orders)
            
            # Format the orders data
            formatting = {
                'price': format_currency,
                'limit_price': format_currency,
                'stop_price': format_currency,
                'qty': format_quantity,
                'filled_qty': format_quantity
            }
            
            create_data_table(orders_df, formatting=formatting)
        else:
            st.info("No open orders")
        
        # New order entry form
        st.subheader("Place New Order")
        
        with st.form("place_order_form"):
            symbol = st.text_input("Symbol", key="new_order_symbol")
            
            order_type = st.selectbox(
                "Order Type",
                options=["market", "limit", "stop", "stop_limit"],
                key="new_order_type"
            )
            
            side = st.selectbox(
                "Side",
                options=["buy", "sell"],
                key="new_order_side"
            )
            
            qty = st.number_input(
                "Quantity",
                min_value=1,
                step=1,
                value=10,
                key="new_order_qty"
            )
            
            # Show price fields based on order type
            limit_price = None
            stop_price = None
            
            if order_type in ["limit", "stop_limit"]:
                limit_price = st.number_input(
                    "Limit Price",
                    min_value=0.01,
                    step=0.01,
                    value=100.00,
                    format="%.2f",
                    key="new_order_limit_price"
                )
            
            if order_type in ["stop", "stop_limit"]:
                stop_price = st.number_input(
                    "Stop Price",
                    min_value=0.01,
                    step=0.01,
                    value=100.00,
                    format="%.2f",
                    key="new_order_stop_price"
                )
            
            submit_button = st.form_submit_button("Place Order")
            
            if submit_button and symbol:
                # Create order data
                order_data = {
                    "symbol": symbol,
                    "qty": qty,
                    "side": side,
                    "type": order_type
                }
                
                if limit_price:
                    order_data["limit_price"] = limit_price
                    
                if stop_price:
                    order_data["stop_price"] = stop_price
                
                # Submit the order
                result = place_order(order_data)
                if result:
                    st.experimental_rerun()
    
    # Trade history
    st.subheader("Trade History")
    trades = get_trade_history()
    
    if trades:
        trades_df = pd.DataFrame(trades)
        
        # Format the trades data
        formatting = {
            'price': format_currency,
            'filled_avg_price': format_currency,
            'filled_qty': format_quantity,
            'profit_loss': format_currency,
        }
        
        create_data_table(trades_df, formatting=formatting)
    else:
        st.info("No trade history available")
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")