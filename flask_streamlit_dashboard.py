"""
Flask-Streamlit Trading Dashboard

This dashboard uses Streamlit for the UI but connects to our existing Flask API 
for all data and trading functionality.

The dashboard provides:
1. Account & market status overview
2. Real-time position monitoring 
3. Active trading setups with price levels
4. Interactive candlestick charts
5. Option chain data for selected tickers
6. Position management controls
7. Trading performance reports
"""

import os
import time
import json
import logging
import datetime
import requests
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API base URL - Flask backend
API_BASE_URL = "http://localhost:5000/api"  # Flask backend runs on port 5000

# Configure the page
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for data that needs to persist between reruns
if 'events' not in st.session_state:
    st.session_state.events = []
    
if 'active_tickers' not in st.session_state:
    st.session_state.active_tickers = []
    
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()
    
if 'api_connected' not in st.session_state:
    st.session_state.api_connected = False

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

# Format helpers
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

# API connection functions
def api_health_check():
    """Check if the API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            st.session_state.api_connected = True
            add_event('system', "Successfully connected to API")
            return True
        else:
            st.session_state.api_connected = False
            add_event('error', f"API health check failed: {response.status_code}")
            return False
    except Exception as e:
        st.session_state.api_connected = False
        add_event('error', f"Error connecting to API: {str(e)}")
        return False

def get_account_data():
    """Get account data from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/account")
        if response.status_code == 200:
            return response.json()
        else:
            add_event('error', f"Failed to fetch account data: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error fetching account data: {str(e)}")
        return None

def get_market_status():
    """Get market status from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/market/status")
        if response.status_code == 200:
            return response.json()
        else:
            add_event('error', f"Failed to fetch market status: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error fetching market status: {str(e)}")
        return None

def get_positions():
    """Get positions from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/execution/positions")
        if response.status_code == 200:
            data = response.json()
            if 'positions' in data:
                return data['positions']
            return []
        else:
            add_event('error', f"Failed to fetch positions: {response.status_code}")
            return []
    except Exception as e:
        add_event('error', f"Error fetching positions: {str(e)}")
        return []

def get_available_tickers():
    """Get available tickers from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/tickers")
        if response.status_code == 200:
            return response.json()
        else:
            add_event('error', f"Failed to fetch tickers: {response.status_code}")
            return []
    except Exception as e:
        add_event('error', f"Error fetching tickers: {str(e)}")
        return []
        
def get_candle_data(ticker, timeframe="1Day", limit=100):
    """Get candle/price data for a ticker from the API"""
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
        else:
            add_event('error', f"Failed to fetch candle data for {ticker}: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        add_event('error', f"Error fetching candle data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_signals(ticker):
    """Get trading signals for a ticker from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/strategy/signals/{ticker}")
        if response.status_code == 200:
            data = response.json()
            if 'signals' in data:
                return data['signals']
            return []
        else:
            add_event('error', f"Failed to fetch signals for {ticker}: {response.status_code}")
            return []
    except Exception as e:
        add_event('error', f"Error fetching signals for {ticker}: {str(e)}")
        return []
        
def get_active_setups():
    """Get active trading setups from the integration API"""
    try:
        response = requests.get(f"{API_BASE_URL}/integration/active-setups")
        if response.status_code == 200:
            data = response.json()
            if 'setups' in data:
                return data['setups']
            return {}
        else:
            add_event('error', f"Failed to fetch active setups: {response.status_code}")
            return {}
    except Exception as e:
        add_event('error', f"Error fetching active setups: {str(e)}")
        return {}

def get_active_trades():
    """Get active trades from the integration API"""
    try:
        response = requests.get(f"{API_BASE_URL}/integration/active-trades")
        if response.status_code == 200:
            data = response.json()
            if 'trades' in data:
                return data['trades']
            return {}
        else:
            add_event('error', f"Failed to fetch active trades: {response.status_code}")
            return {}
    except Exception as e:
        add_event('error', f"Error fetching active trades: {str(e)}")
        return {}
        
def get_trade_history():
    """Get trade history from the integration API"""
    try:
        response = requests.get(f"{API_BASE_URL}/integration/trade-history")
        if response.status_code == 200:
            data = response.json()
            if 'history' in data:
                return data['history']
            return {}
        else:
            add_event('error', f"Failed to fetch trade history: {response.status_code}")
            return {}
    except Exception as e:
        add_event('error', f"Error fetching trade history: {str(e)}")
        return {}
        
def get_performance_report():
    """Get performance report from the integration API"""
    try:
        response = requests.get(f"{API_BASE_URL}/integration/performance-report")
        if response.status_code == 200:
            data = response.json()
            if 'report' in data:
                return data['report']
            return None
        else:
            add_event('error', f"Failed to fetch performance report: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error fetching performance report: {str(e)}")
        return None

def evaluate_setups():
    """Trigger setup evaluation from the integration API"""
    try:
        response = requests.post(f"{API_BASE_URL}/integration/evaluate")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                count = data.get('processed_count', 0)
                add_event('signal', f"Evaluated setups: {count} processed")
            return data
        else:
            add_event('error', f"Failed to evaluate setups: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error evaluating setups: {str(e)}")
        return None

def monitor_trades():
    """Trigger trade monitoring from the integration API"""
    try:
        response = requests.post(f"{API_BASE_URL}/integration/monitor")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                count = data.get('updated_count', 0)
                add_event('signal', f"Monitored trades: {count} updated")
            return data
        else:
            add_event('error', f"Failed to monitor trades: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error monitoring trades: {str(e)}")
        return None

def place_order(symbol, qty, side):
    """Place an order via the API"""
    try:
        payload = {
            'symbol': symbol,
            'qty': qty,
            'side': side
        }
        response = requests.post(f"{API_BASE_URL}/execution/order", json=payload)
        if response.status_code == 200:
            data = response.json()
            add_event('signal', f"Order placed: {side} {qty} shares of {symbol}")
            return data
        else:
            add_event('error', f"Failed to place order: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error placing order: {str(e)}")
        return None

def close_position(symbol, percentage=1.0):
    """Close a position via the API"""
    try:
        payload = {
            'percentage': percentage
        }
        response = requests.post(f"{API_BASE_URL}/execution/close/{symbol}", json=payload)
        if response.status_code == 200:
            data = response.json()
            add_event('signal', f"Position closed: {symbol}")
            return data
        else:
            add_event('error', f"Failed to close position: {response.status_code}")
            return None
    except Exception as e:
        add_event('error', f"Error closing position: {str(e)}")
        return None

# Chart creation function using Plotly
def create_candlestick_chart(symbol, data=None):
    """Create a candlestick chart for a given ticker symbol"""
    if data is None or len(data) == 0:
        # Fetch data from API
        data = get_candle_data(symbol)
        
    if data is None or len(data) == 0:
        # Create an empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title=f"{symbol} - No Data Available",
            height=400
        )
        return fig
    
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
    if 'volume' in data.columns:
        fig.add_trace(
            go.Bar(
                x=data['timestamp'],
                y=data['volume'],
                name='Volume',
                marker=dict(color='rgba(100, 100, 255, 0.5)')
            ),
            row=2, col=1
        )
    
    # Get signals for this ticker and add to chart
    signals = get_signals(symbol)
    for signal in signals:
        if 'trigger' in signal and 'price' in signal['trigger']:
            fig.add_hline(
                y=signal['trigger']['price'],
                line_width=1, 
                line_dash="dash",
                line_color="red",
                annotation_text=f"{signal['category']} ({signal['trigger']['price']})",
                row=1, col=1
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

# Refresh data periodically
def refresh_data():
    """Refresh all data from the API"""
    st.session_state.last_refresh = datetime.datetime.now()
    
    # Evaluate setups and monitor trades
    evaluate_setups()
    monitor_trades()
    
    add_event('system', "Data refreshed")

# Sidebar
with st.sidebar:
    st.title("Trading Dashboard")
    
    # API connection status
    if api_health_check():
        st.success("Connected to API")
    else:
        st.error("API Connection Failed")
        st.info("Make sure the Flask backend is running on port 5000")
    
    # Refresh button
    if st.button("Refresh Data"):
        refresh_data()
    
    # Get available tickers
    available_tickers = get_available_tickers()
    if not available_tickers:
        available_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    # Ticker selection
    st.header("Ticker Selection")
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
            result = place_order(order_symbol, order_quantity, order_side.lower())
            if result:
                st.success(f"Order placed: {order_side} {order_quantity} shares of {order_symbol}")
            else:
                st.error("Failed to place order")

# Main dashboard
st.title("Trading Dashboard")

# Account information row
account = get_account_data()
col1, col2, col3, col4 = st.columns(4)

with col1:
    equity_value = account.get('equity', 0) if account else 0
    st.metric(
        label="Account Equity",
        value=format_currency(equity_value)
    )

with col2:
    buying_power = account.get('buying_power', 0) if account else 0
    st.metric(
        label="Buying Power",
        value=format_currency(buying_power)
    )

with col3:
    # Get market status
    market_data = get_market_status()
    if market_data and 'is_open' in market_data:
        market_status = "Open" if market_data['is_open'] else "Closed"
        if market_data['is_open'] and 'next_close' in market_data:
            next_time = market_data['next_close']
            time_label = "Market Closes"
        elif not market_data['is_open'] and 'next_open' in market_data:
            next_time = market_data['next_open']
            time_label = "Market Opens"
        else:
            next_time = None
            time_label = ""
        
        if next_time:
            next_time_str = next_time.strftime("%H:%M:%S") if isinstance(next_time, datetime.datetime) else str(next_time)
            st.metric(
                label=f"Market Status: {market_status}",
                value=f"{time_label} at {next_time_str}"
            )
        else:
            st.metric(
                label="Market Status",
                value=market_status
            )
    else:
        # Fallback if API doesn't provide status
        market_status = "Unknown"
        st.metric(
            label="Market Status",
            value=market_status
        )

with col4:
    positions = get_positions()
    position_count = len(positions)
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
                # Create chart using data from API
                fig = create_candlestick_chart(ticker)
                st.plotly_chart(fig, use_container_width=True)
                
                # Add trading buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Buy {ticker}", key=f"buy_{ticker}"):
                        result = place_order(ticker, 10, "buy")
                        if result:
                            st.success(f"Bought 10 shares of {ticker}")
                with col2:
                    if st.button(f"Sell {ticker}", key=f"sell_{ticker}"):
                        result = place_order(ticker, 10, "sell")
                        if result:
                            st.success(f"Sold 10 shares of {ticker}")

# Trading Setups section
st.header("Trading Setups")
st.markdown("---")

# Get active trading setups
active_setups = get_active_setups()
if not active_setups:
    st.info("No active setups detected")
else:
    # Convert to list of dicts for easier display
    setup_list = []
    for setup_id, setup in active_setups.items():
        setup_data = {
            'setup_id': setup_id,
            'ticker': setup.get('primary_ticker', ''),
            'signal': setup.get('signal_type', ''),
            'bias': setup.get('bias', ''),
            'status': setup.get('status', ''),
            'confidence': setup.get('confidence', 0),
            'timestamp': setup.get('timestamp', '')
        }
        setup_list.append(setup_data)
    
    # Create DataFrame
    setups_df = pd.DataFrame(setup_list)
    
    # Format columns
    if not setups_df.empty:
        if 'timestamp' in setups_df.columns:
            setups_df['timestamp'] = pd.to_datetime(setups_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        if 'confidence' in setups_df.columns:
            setups_df['confidence'] = setups_df['confidence'].apply(lambda x: f"{x*100:.0f}%" if x else "")
    
    # Display setups table
    st.subheader(f"Active Setups ({len(setup_list)})")
    st.dataframe(setups_df, use_container_width=True)
    
    # Add a button to evaluate setups
    if st.button("Evaluate Trading Setups"):
        result = evaluate_setups()
        if result and result.get('success'):
            st.success(f"Evaluated setups: {result.get('processed_count', 0)} processed")
        else:
            st.warning("No new setups to process at this time")

# Active Trades section
st.header("Active Trades")
st.markdown("---")

# Get active trades
active_trades = get_active_trades()
if not active_trades:
    st.info("No active trades at this time")
else:
    # Convert to list of dicts for easier display
    trade_list = []
    for setup_id, trade in active_trades.items():
        trade_data = trade.get('trade_data', {})
        trade_info = {
            'setup_id': setup_id,
            'ticker': trade.get('primary_ticker', ''),
            'signal': trade.get('signal_type', ''),
            'entry_price': trade_data.get('entry_price', ''),
            'current_price': trade_data.get('current_price', ''),
            'p&l': trade_data.get('profit_loss', 0),
            'quantity': trade_data.get('quantity', ''),
            'status': trade_data.get('status', '')
        }
        trade_list.append(trade_info)
    
    # Create DataFrame
    trades_df = pd.DataFrame(trade_list)
    
    # Format columns
    if not trades_df.empty:
        if 'p&l' in trades_df.columns:
            trades_df['p&l'] = trades_df['p&l'].apply(lambda x: f"{x:.2f}%" if x is not None else "")
        
        # Format prices as currency
        for col in ['entry_price', 'current_price']:
            if col in trades_df.columns:
                trades_df[col] = trades_df[col].apply(lambda x: format_currency(x) if x else "")
    
    # Display trades table
    st.subheader(f"Active Trades ({len(trade_list)})")
    st.dataframe(trades_df, use_container_width=True)
    
    # Add a button to monitor trades
    if st.button("Monitor Active Trades"):
        result = monitor_trades()
        if result and result.get('success'):
            st.success(f"Monitored trades: {result.get('updated_count', 0)} updated")
        else:
            st.warning("No trades updated at this time")

# Positions table
st.header("Positions")
st.markdown("---")

positions = get_positions()
if not positions:
    st.info("No open positions")
else:
    # Create a DataFrame for positions
    positions_df = pd.DataFrame(positions)
    
    # Format values for display
    if 'unrealized_pl' in positions_df.columns:
        positions_df['unrealized_pl'] = positions_df['unrealized_pl'].apply(lambda x: f"${float(x):.2f}" if x else "$0.00")
    if 'unrealized_plpc' in positions_df.columns:
        positions_df['unrealized_plpc'] = positions_df['unrealized_plpc'].apply(lambda x: f"{float(x)*100:.2f}%" if x else "0.00%")
    
    st.dataframe(positions_df, use_container_width=True)

# Performance Report section
st.header("Trading Performance")
st.markdown("---")

# Get performance report
performance_report = get_performance_report()

if not performance_report or 'total_trades' not in performance_report or performance_report['total_trades'] == 0:
    st.info("No trading history available for performance analysis")
else:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Trades",
            value=str(performance_report.get('total_trades', 0))
        )
    
    with col2:
        win_rate = performance_report.get('win_rate', 0) * 100
        st.metric(
            label="Win Rate",
            value=f"{win_rate:.1f}%"
        )
    
    with col3:
        avg_profit = performance_report.get('avg_profit_loss', 0)
        st.metric(
            label="Avg P/L Per Trade",
            value=f"{avg_profit:.2f}%",
            delta=None
        )
    
    with col4:
        total_pl = performance_report.get('total_profit_loss', 0)
        st.metric(
            label="Total P/L",
            value=f"{total_pl:.2f}%",
            delta=None
        )
    
    # Performance by ticker
    st.subheader("Performance by Ticker")
    ticker_performance = performance_report.get('ticker_performance', {})
    
    if not ticker_performance:
        st.info("No ticker-specific performance data available")
    else:
        ticker_data = []
        for ticker, data in ticker_performance.items():
            ticker_data.append({
                'ticker': ticker,
                'trades': data.get('trades', 0),
                'winning': data.get('winning', 0),
                'losing': data.get('losing', 0),
                'win_rate': data.get('winning', 0) / data.get('trades', 1) * 100 if data.get('trades', 0) > 0 else 0,
                'total_pl': data.get('total_pl', 0)
            })
        
        ticker_df = pd.DataFrame(ticker_data)
        
        # Format columns
        if not ticker_df.empty:
            ticker_df['win_rate'] = ticker_df['win_rate'].apply(lambda x: f"{x:.1f}%")
            ticker_df['total_pl'] = ticker_df['total_pl'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(ticker_df, use_container_width=True)
    
    # Best and worst tickers
    best_ticker = performance_report.get('best_ticker')
    worst_ticker = performance_report.get('worst_ticker')
    
    if best_ticker or worst_ticker:
        st.subheader("Top Performers")
        col1, col2 = st.columns(2)
        
        with col1:
            if best_ticker:
                st.success(f"Best: {best_ticker}")
        
        with col2:
            if worst_ticker:
                st.error(f"Worst: {worst_ticker}")
    
    # Recent trade history
    st.subheader("Recent Trades")
    trades = performance_report.get('trades', [])
    
    if not trades:
        st.info("No recent trades to display")
    else:
        # Only show the 10 most recent trades
        recent_trades = trades[:10] if len(trades) > 10 else trades
        
        trade_history = []
        for trade in recent_trades:
            trade_data = trade.get('trade_data', {})
            trade_info = {
                'ticker': trade.get('primary_ticker', ''),
                'signal': trade.get('signal_type', ''),
                'entry_price': trade_data.get('entry_price', ''),
                'exit_price': trade_data.get('exit_price', ''),
                'p&l': trade_data.get('profit_loss', 0),
                'status': trade_data.get('status', '')
            }
            trade_history.append(trade_info)
        
        history_df = pd.DataFrame(trade_history)
        
        # Format columns
        if not history_df.empty:
            if 'p&l' in history_df.columns:
                history_df['p&l'] = history_df['p&l'].apply(lambda x: f"{x:.2f}%" if x is not None else "")
            
            # Format prices as currency
            for col in ['entry_price', 'exit_price']:
                if col in history_df.columns:
                    history_df[col] = history_df[col].apply(lambda x: format_currency(x) if x else "")
        
        st.dataframe(history_df, use_container_width=True)
    positions_df['avg_entry_price'] = positions_df['avg_entry_price'].apply(lambda x: f"${float(x):.2f}")
    positions_df['current_price'] = positions_df['current_price'].apply(lambda x: f"${float(x):.2f}")
    positions_df['market_value'] = positions_df['market_value'].apply(lambda x: f"${float(x):.2f}")
    
    # Rename columns for better display
    columns_mapping = {
        'symbol': 'Symbol',
        'qty': 'Quantity',
        'avg_entry_price': 'Entry Price',
        'current_price': 'Current Price',
        'unrealized_pl': 'Unrealized P/L',
        'unrealized_plpc': 'P/L %',
        'market_value': 'Market Value'
    }
    positions_df = positions_df.rename(columns=columns_mapping)
    
    # Display the positions table
    st.dataframe(positions_df, use_container_width=True)
    
    # Add close all positions button
    if st.button("Close All Positions"):
        for position in positions:
            close_position(position['symbol'])
        st.success("Request to close all positions sent")

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

# Set up auto-refresh
# Using JavaScript to refresh the page every 30 seconds
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
if auto_refresh:
    refresh_interval = 30  # seconds
    st.markdown(
        f"""
        <script>
            setTimeout(function(){{
                window.location.reload();
            }}, {refresh_interval * 1000});
        </script>
        """,
        unsafe_allow_html=True
    )