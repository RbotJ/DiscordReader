"""
Trading Dashboard - Streamlit App

A full-featured trading dashboard built with Streamlit that connects to Alpaca API
for real-time market data and trading functionality.
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

# Alpaca imports
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest, MarketOrderRequest
from alpaca.trading.enums import AssetClass, OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.live import StockDataStream

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for data persistence
if 'events' not in st.session_state:
    st.session_state.events = []

if 'account' not in st.session_state:
    st.session_state.account = None
    
if 'positions' not in st.session_state:
    st.session_state.positions = []

if 'active_tickers' not in st.session_state:
    st.session_state.active_tickers = []

if 'available_tickers' not in st.session_state:
    st.session_state.available_tickers = []
    
if 'market_data' not in st.session_state:
    st.session_state.market_data = {}
    
if 'signals' not in st.session_state:
    st.session_state.signals = []

if 'data_stream' not in st.session_state:
    st.session_state.data_stream = None
    
if 'clock' not in st.session_state:
    st.session_state.clock = None
    
if 'refresh_time' not in st.session_state:
    st.session_state.refresh_time = datetime.datetime.now()

# Lock for thread-safe updates
data_lock = Lock()

# Helper functions
def add_event(event_type, message):
    """Add an event to the event log"""
    with data_lock:
        event = {
            'id': f"event-{time.time()}",
            'type': event_type,
            'timestamp': datetime.datetime.now(),
            'message': message
        }
        st.session_state.events.insert(0, event)  # Add to the beginning
        # Keep only the most recent 50 events
        if len(st.session_state.events) > 50:
            st.session_state.events = st.session_state.events[:50]
    
def format_currency(value):
    """Format a value as USD currency"""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"

def format_percent(value):
    """Format a value as a percentage"""
    if value is None:
        return "0.00%"
    return f"{value:.2f}%"

def get_timeframe_bars(symbol, timeframe=TimeFrame.Day, limit=100):
    """Get historical bars for a ticker symbol"""
    try:
        # If we don't have API credentials yet, return sample data
        if not st.session_state.get('api_key') or not st.session_state.get('api_secret'):
            add_event('system', f"Using sample data for {symbol}")
            # Generate sample data for demo purposes
            dates = pd.date_range(end=datetime.datetime.now(), periods=limit, freq='1min')
            base_price = 150 + np.random.rand() * 100
            price_data = base_price + np.cumsum(np.random.randn(limit) * 0.5)
            volume_data = np.random.randint(100, 10000, size=limit)
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': price_data,
                'high': price_data + np.random.rand(limit) * 0.5,
                'low': price_data - np.random.rand(limit) * 0.5,
                'close': price_data,
                'volume': volume_data
            })
            return df
        
        # Create a historical data client
        historical_client = StockHistoricalDataClient(
            api_key=st.session_state.api_key,
            secret_key=st.session_state.api_secret
        )
        
        # Define the request parameters
        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=timeframe,
            limit=limit
        )
        
        # Get the bars data
        bars = historical_client.get_stock_bars(request_params)
        
        # Convert to a DataFrame for easier manipulation
        df = bars.df.reset_index()
        
        # If we have multi-level columns due to multiple symbols, adjust
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(0)
        
        return df
    
    except Exception as e:
        add_event('error', f"Error fetching data for {symbol}: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def create_candlestick_chart(symbol, data=None):
    """Create a candlestick chart for the given symbol"""
    if data is None or len(data) == 0:
        # Get historical data for the symbol
        data = get_timeframe_bars(symbol)
        
    if len(data) == 0:
        # Return an empty figure if we don't have data
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
    
    # Add any signals if available
    ticker_signals = [s for s in st.session_state.signals if s.get('symbol') == symbol]
    for signal in ticker_signals:
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

def init_alpaca_clients():
    """Initialize Alpaca clients with API credentials"""
    if not st.session_state.get('api_key') or not st.session_state.get('api_secret'):
        add_event('system', "API credentials not configured. Using demo mode.")
        return False
    
    try:
        # Initialize the trading client
        trading_client = TradingClient(
            api_key=st.session_state.api_key,
            secret_key=st.session_state.api_secret,
            paper=True  # Use paper trading
        )
        
        # Get account information
        account = trading_client.get_account()
        st.session_state.account = {
            'id': account.id,
            'equity': float(account.equity),
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'day_trade_count': account.day_trade_count,
            'status': account.status
        }
        
        # Get market clock
        clock = trading_client.get_clock()
        st.session_state.clock = {
            'is_open': clock.is_open,
            'next_open': clock.next_open,
            'next_close': clock.next_close,
            'timestamp': clock.timestamp
        }
        
        # Get positions
        positions = trading_client.get_all_positions()
        st.session_state.positions = [{
            'symbol': position.symbol,
            'qty': float(position.qty),
            'avg_entry_price': float(position.avg_entry_price),
            'current_price': float(position.current_price),
            'unrealized_pl': float(position.unrealized_pl),
            'unrealized_plpc': float(position.unrealized_plpc),
            'market_value': float(position.market_value)
        } for position in positions]
        
        # Get available assets (for the ticker list)
        assets = trading_client.get_all_assets(
            GetAssetsRequest(
                status='active',
                asset_class=AssetClass.US_EQUITY
            )
        )
        
        # Filter for common stocks that are tradable
        tradable_symbols = [asset.symbol for asset in assets 
                          if asset.tradable and asset.symbol.isalpha() 
                          and len(asset.symbol) < 5]
        
        # Limit to top 100 common stocks for the demo
        top_symbols = sorted(tradable_symbols)[:100]
        st.session_state.available_tickers = top_symbols
        
        add_event('system', "Alpaca clients initialized successfully")
        return True
    
    except Exception as e:
        add_event('error', f"Error initializing Alpaca clients: {str(e)}")
        return False

def start_market_data_stream():
    """Start the WebSocket connection for real-time market data"""
    if 'data_stream' in st.session_state and st.session_state.data_stream:
        # Already connected
        return
        
    if not st.session_state.get('api_key') or not st.session_state.get('api_secret'):
        add_event('system', "API credentials not configured. Cannot start real-time data stream.")
        return
    
    try:
        # Initialize the data stream
        data_stream = StockDataStream(
            api_key=st.session_state.api_key,
            secret_key=st.session_state.api_secret
        )
        
        async def handle_bar(bar):
            """Handle incoming bar data"""
            with data_lock:
                symbol = bar.symbol
                # Store the latest bar data
                if symbol not in st.session_state.market_data:
                    st.session_state.market_data[symbol] = []
                
                bar_data = {
                    'timestamp': bar.timestamp,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                }
                
                st.session_state.market_data[symbol].append(bar_data)
                
                # Keep only the last 100 bars
                if len(st.session_state.market_data[symbol]) > 100:
                    st.session_state.market_data[symbol] = st.session_state.market_data[symbol][-100:]
                
                # Force UI refresh on next rerun
                st.session_state.refresh_time = datetime.datetime.now()
                
                # Log event for new bar data
                add_event('market', f"{symbol} new bar: ${bar.close:.2f}")
        
        async def handle_quote(quote):
            """Handle incoming quote data"""
            # This is high frequency data, so we only log occasionally
            if np.random.random() < 0.05:  # Only log ~5% of quotes to avoid flooding
                add_event('market', f"{quote.symbol} quote: ${quote.ask_price:.2f} x {quote.ask_size} | ${quote.bid_price:.2f} x {quote.bid_size}")
        
        async def handle_trade(trade):
            """Handle incoming trade data"""
            # This is high frequency data, so we only log occasionally
            if np.random.random() < 0.02:  # Only log ~2% of trades to avoid flooding
                add_event('market', f"{trade.symbol} trade: ${trade.price:.2f} x {trade.size}")
                
        # Subscribe to the active tickers
        for ticker in st.session_state.active_tickers:
            data_stream.subscribe_bars(handle_bar, ticker)
            # Optionally subscribe to quotes and trades as well
            # data_stream.subscribe_quotes(handle_quote, ticker)
            # data_stream.subscribe_trades(handle_trade, ticker)
            
        # Store the data stream in session state
        st.session_state.data_stream = data_stream
        
        # Start the data stream in a background thread
        def start_stream_thread():
            data_stream.run()
            
        stream_thread = Thread(target=start_stream_thread, daemon=True)
        stream_thread.start()
        
        add_event('system', "Real-time market data stream started")
        
    except Exception as e:
        add_event('error', f"Error starting market data stream: {str(e)}")

def update_ticker_subscription(symbol, subscribe=True):
    """Subscribe or unsubscribe to a ticker"""
    if not st.session_state.get('data_stream'):
        add_event('warning', "Data stream not initialized. Cannot update subscription.")
        return
    
    data_stream = st.session_state.data_stream
    
    try:
        if subscribe:
            if symbol not in st.session_state.active_tickers:
                st.session_state.active_tickers.append(symbol)
                
            # Subscribe to real-time data for this ticker
            async def handle_bar(bar):
                with data_lock:
                    if symbol not in st.session_state.market_data:
                        st.session_state.market_data[symbol] = []
                    
                    bar_data = {
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume
                    }
                    
                    st.session_state.market_data[symbol].append(bar_data)
                    # Keep only the last 100 bars
                    if len(st.session_state.market_data[symbol]) > 100:
                        st.session_state.market_data[symbol] = st.session_state.market_data[symbol][-100:]
                    
                    # Force UI refresh on next rerun
                    st.session_state.refresh_time = datetime.datetime.now()
            
            data_stream.subscribe_bars(handle_bar, symbol)
            add_event('system', f"Subscribed to {symbol}")
        else:
            if symbol in st.session_state.active_tickers:
                st.session_state.active_tickers.remove(symbol)
                
            # Unsubscribe from real-time data for this ticker
            data_stream.unsubscribe_bars(symbol)
            add_event('system', f"Unsubscribed from {symbol}")
    
    except Exception as e:
        add_event('error', f"Error updating subscription for {symbol}: {str(e)}")

def place_market_order(symbol, qty, side):
    """Place a market order"""
    if not st.session_state.get('api_key') or not st.session_state.get('api_secret'):
        add_event('error', "API credentials not configured. Cannot place order.")
        return False
    
    try:
        # Initialize the trading client
        trading_client = TradingClient(
            api_key=st.session_state.api_key,
            secret_key=st.session_state.api_secret,
            paper=True  # Use paper trading
        )
        
        # Create the order request
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit the order
        order = trading_client.submit_order(order_request)
        
        # Log the order submission
        add_event('signal', f"Order placed: {side.name} {qty} shares of {symbol}")
        
        # Refresh positions
        positions = trading_client.get_all_positions()
        st.session_state.positions = [{
            'symbol': position.symbol,
            'qty': float(position.qty),
            'avg_entry_price': float(position.avg_entry_price),
            'current_price': float(position.current_price),
            'unrealized_pl': float(position.unrealized_pl),
            'unrealized_plpc': float(position.unrealized_plpc),
            'market_value': float(position.market_value)
        } for position in positions]
        
        return True
    
    except Exception as e:
        add_event('error', f"Error placing order for {symbol}: {str(e)}")
        return False

def close_position(symbol, percentage=1.0):
    """Close a position"""
    if not st.session_state.get('api_key') or not st.session_state.get('api_secret'):
        add_event('error', "API credentials not configured. Cannot close position.")
        return False
    
    try:
        # Initialize the trading client
        trading_client = TradingClient(
            api_key=st.session_state.api_key,
            secret_key=st.session_state.api_secret,
            paper=True  # Use paper trading
        )
        
        # Find the position
        position = None
        for pos in st.session_state.positions:
            if pos['symbol'] == symbol:
                position = pos
                break
                
        if not position:
            add_event('error', f"No position found for {symbol}")
            return False
        
        # Calculate the quantity to close
        qty = float(position['qty']) * percentage
        
        # Determine the side (opposite of the position)
        side = OrderSide.SELL if float(position['qty']) > 0 else OrderSide.BUY
        
        # Create the order request
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit the order
        order = trading_client.submit_order(order_request)
        
        # Log the order submission
        add_event('signal', f"Position closed: {side.name} {qty} shares of {symbol}")
        
        # Refresh positions
        positions = trading_client.get_all_positions()
        st.session_state.positions = [{
            'symbol': position.symbol,
            'qty': float(position.qty),
            'avg_entry_price': float(position.avg_entry_price),
            'current_price': float(position.current_price),
            'unrealized_pl': float(position.unrealized_pl),
            'unrealized_plpc': float(position.unrealized_plpc),
            'market_value': float(position.market_value)
        } for position in positions]
        
        return True
    
    except Exception as e:
        add_event('error', f"Error closing position for {symbol}: {str(e)}")
        return False

def refresh_data():
    """Refresh all data from the API"""
    init_alpaca_clients()
    
    # Force UI refresh on next rerun
    st.session_state.refresh_time = datetime.datetime.now()
    
    add_event('system', "Data refreshed")

# Sidebar
with st.sidebar:
    st.title("Trading Dashboard")
    
    # API credentials
    st.header("Alpaca API Configuration")
    api_key = st.text_input("API Key", value=st.session_state.get('api_key', ''), type="password")
    api_secret = st.text_input("API Secret", value=st.session_state.get('api_secret', ''), type="password")
    
    if st.button("Connect"):
        if api_key and api_secret:
            st.session_state.api_key = api_key
            st.session_state.api_secret = api_secret
            add_event('system', "API credentials saved")
            init_alpaca_clients()
            start_market_data_stream()
        else:
            st.error("Please enter both API key and secret")
    
    # Refresh data button
    if st.button("Refresh Data"):
        refresh_data()
    
    # Ticker selection
    st.header("Ticker Selection")
    if len(st.session_state.available_tickers) > 0:
        selected_tickers = st.multiselect(
            "Select tickers to track",
            options=st.session_state.available_tickers,
            default=st.session_state.active_tickers
        )
        
        # Update subscriptions if selection changed
        if selected_tickers != st.session_state.active_tickers:
            # Add new tickers
            for ticker in selected_tickers:
                if ticker not in st.session_state.active_tickers:
                    update_ticker_subscription(ticker, subscribe=True)
            
            # Remove unselected tickers
            for ticker in st.session_state.active_tickers.copy():
                if ticker not in selected_tickers:
                    update_ticker_subscription(ticker, subscribe=False)
            
            st.session_state.active_tickers = selected_tickers
    else:
        st.warning("Connect to Alpaca API to load available tickers")
        
        # Demo tickers selection when not connected
        demo_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
        selected_demo = st.multiselect(
            "Select demo tickers to track",
            options=demo_tickers,
            default=st.session_state.active_tickers
        )
        
        if selected_demo != st.session_state.active_tickers:
            st.session_state.active_tickers = selected_demo
            add_event('system', f"Demo tickers selected: {', '.join(selected_demo)}")
    
    # Order entry form
    st.header("Quick Trade")
    with st.form("order_form"):
        order_symbol = st.selectbox("Symbol", options=[""] + st.session_state.active_tickers)
        order_quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        order_side = st.radio("Side", options=["Buy", "Sell"])
        
        submit_order = st.form_submit_button("Place Order")
        
        if submit_order and order_symbol:
            side = OrderSide.BUY if order_side == "Buy" else OrderSide.SELL
            success = place_market_order(order_symbol, order_quantity, side)
            if success:
                st.success(f"Order placed: {order_side} {order_quantity} shares of {order_symbol}")
            else:
                st.error("Failed to place order. Check logs for details.")

# Main dashboard layout
st.title("Trading Dashboard")

# Account information row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Account Equity",
        value=format_currency(st.session_state.account.get('equity') if st.session_state.account else None)
    )

with col2:
    st.metric(
        label="Buying Power",
        value=format_currency(st.session_state.account.get('buying_power') if st.session_state.account else None)
    )

with col3:
    market_status = "Open" if st.session_state.clock and st.session_state.clock.get('is_open') else "Closed"
    next_time = None
    
    if st.session_state.clock:
        if st.session_state.clock.get('is_open'):
            next_time = st.session_state.clock.get('next_close')
            time_label = "Market Closes"
        else:
            next_time = st.session_state.clock.get('next_open')
            time_label = "Market Opens"
    
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
    charts_per_row = min(len(st.session_state.active_tickers), 3)
    
    # Split tickers into rows of charts_per_row
    ticker_rows = [st.session_state.active_tickers[i:i+charts_per_row] 
                for i in range(0, len(st.session_state.active_tickers), charts_per_row)]
    
    # Create a row for each group of tickers
    for row_tickers in ticker_rows:
        cols = st.columns(len(row_tickers))
        
        for i, ticker in enumerate(row_tickers):
            with cols[i]:
                # Check if we have real-time data for this ticker
                if ticker in st.session_state.market_data and len(st.session_state.market_data[ticker]) > 0:
                    # Convert to a DataFrame
                    df = pd.DataFrame(st.session_state.market_data[ticker])
                    fig = create_candlestick_chart(ticker, df)
                else:
                    # Use historical data
                    fig = create_candlestick_chart(ticker)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add trading buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Buy {ticker}", key=f"buy_{ticker}"):
                        place_market_order(ticker, 1, OrderSide.BUY)
                with col2:
                    if st.button(f"Sell {ticker}", key=f"sell_{ticker}"):
                        place_market_order(ticker, 1, OrderSide.SELL)

# Positions table
st.header("Positions")

if not st.session_state.positions:
    st.info("No open positions")
else:
    # Create a DataFrame for the positions
    positions_df = pd.DataFrame(st.session_state.positions)
    
    # Format the DataFrame for display
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
        for position in st.session_state.positions:
            close_position(position['symbol'])
        st.success("All positions closed")

# Event log
st.header("Event Log")

if not st.session_state.events:
    st.info("No events yet")
else:
    # Create containers for different event types
    event_container = st.container()
    
    with event_container:
        # Group events for more compact display
        for event in st.session_state.events[:20]:  # Show only the most recent 20
            event_time = event['timestamp'].strftime('%H:%M:%S') if isinstance(event['timestamp'], datetime.datetime) else str(event['timestamp'])
            
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

# Initialize with demo events if empty
if not st.session_state.events:
    add_event('system', "Dashboard initialized")
    add_event('system', "Welcome to the Trading Dashboard")
    add_event('system', "Select tickers from the sidebar to get started")

# Set up automatic refresh (every 30 seconds)
# Streamlit will automatically rerun the script when a widget value changes
# We use the refresh button for manual refreshes