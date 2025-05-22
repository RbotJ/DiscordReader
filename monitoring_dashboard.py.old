"""
Trade Monitoring Dashboard

A Streamlit dashboard for monitoring trade setups, prices, and signals.
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
API_URL = "http://localhost:5000/api"
DEFAULT_TIMEFRAMES = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
DEFAULT_PERIOD = 20  # Number of candles to show by default

# Setup page config
st.set_page_config(
    page_title="A+ Trading Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Utility functions
def format_currency(value):
    """Format a value as USD currency"""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"

def format_percent(value):
    """Format a value as a percentage"""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"

def fetch_api_data(endpoint, params=None):
    """Fetch data from the API"""
    try:
        response = requests.get(f"{API_URL}/{endpoint}", params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return None

def fetch_tickers():
    """Fetch available tickers from the API"""
    data = fetch_api_data("tickers")
    if data and "tickers" in data:
        return data["tickers"]
    return []

def fetch_candle_data(ticker, timeframe="1Day", limit=100):
    """Fetch candle data for a ticker"""
    data = fetch_api_data(f"candles/{ticker}", params={"timeframe": timeframe, "limit": limit})
    if data and "candles" in data:
        return data["candles"]
    return []

def fetch_signals(ticker):
    """Fetch trading signals for a ticker"""
    data = fetch_api_data(f"signals/{ticker}")
    if data and "signals" in data:
        return data["signals"]
    return []

def create_candlestick_chart(ticker, candles, signals=None):
    """Create a candlestick chart with signals"""
    if not candles:
        return None

    # Convert to DataFrame
    df = pd.DataFrame(candles)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Create figure
    fig = go.Figure()

    # Add candlestick chart
    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price"
    ))

    # Add volume as a bar chart
    if "volume" in df.columns:
        fig.add_trace(go.Bar(
            x=df["timestamp"],
            y=df["volume"],
            name="Volume",
            marker_color="rgba(128, 128, 128, 0.5)",
            yaxis="y2"
        ))

    # Add signals if available
    if signals:
        for signal in signals:
            if signal["status"] == "active" and "trigger" in signal:
                trigger_price = signal["trigger"].get("price")
                if trigger_price:
                    fig.add_shape(
                        type="line",
                        x0=df["timestamp"].min(),
                        x1=df["timestamp"].max(),
                        y0=trigger_price,
                        y1=trigger_price,
                        line=dict(
                            color="red" if signal["category"] == "breakdown" else "green",
                            width=2,
                            dash="dash",
                        ),
                    )

                    # Add annotation
                    fig.add_annotation(
                        x=df["timestamp"].max(),
                        y=trigger_price,
                        text=f"{signal['category']} {trigger_price:.2f}",
                        showarrow=False,
                        font=dict(
                            size=12,
                            color="red" if signal["category"] == "breakdown" else "green"
                        ),
                        xshift=10
                    )

    # Set layout
    fig.update_layout(
        title=f"{ticker} Price Chart",
        xaxis_title="Date",
        yaxis_title="Price",
        height=500,
        xaxis_rangeslider_visible=False,
        yaxis2=dict(
            title="Volume",
            overlaying="y",
            side="right",
            showgrid=False
        )
    )

    return fig

def main():
    """Main dashboard application"""
    # Sidebar
    st.sidebar.title("A+ Trading Monitor")
    st.sidebar.markdown("Monitor trade setups and signals")

    # Refresh button
    if st.sidebar.button("Refresh Data"):
        st.rerun()

    # Get available tickers
    tickers = fetch_tickers()

    if not tickers:
        st.warning("No tickers available. Please check the API connection.")
        if st.button("Try Again"):
            st.rerun()
        return

    # Select ticker
    selected_ticker = st.sidebar.selectbox("Select Ticker", tickers)

    # Select timeframe
    timeframe = st.sidebar.selectbox("Timeframe", DEFAULT_TIMEFRAMES)

    # Get candle data and signals
    candles = fetch_candle_data(selected_ticker, timeframe=timeframe, limit=DEFAULT_PERIOD)
    signals = fetch_signals(selected_ticker)

    # Main area
    st.title(f"{selected_ticker} Trading Monitor")

    # Price and signal metrics
    col1, col2, col3, col4 = st.columns(4)

    # Get latest price
    latest_price = None
    if candles:
        latest_price = candles[-1]["close"]

    with col1:
        st.metric("Current Price", format_currency(latest_price) if latest_price else "N/A")

    # Signal summary
    active_signals = [s for s in signals if s.get("status") == "active"]
    with col2:
        st.metric("Active Signals", len(active_signals))

    # Display day change
    day_change = None
    day_change_pct = None
    if len(candles) >= 2:
        day_change = candles[-1]["close"] - candles[-2]["close"]
        day_change_pct = (day_change / candles[-2]["close"]) * 100

    with col3:
        st.metric(
            "Day Change", 
            format_currency(day_change) if day_change is not None else "N/A",
            format_percent(day_change_pct) if day_change_pct is not None else "N/A",
            delta_color="normal"
        )

    # Candlestick chart
    st.subheader("Price Chart")
    chart = create_candlestick_chart(selected_ticker, candles, signals)
    if chart:
        st.plotly_chart(chart, use_container_width=True)
    else:
        st.warning(f"No candle data available for {selected_ticker}")

    # Active signals
    st.subheader("Active Trading Signals")
    if active_signals:
        for i, signal in enumerate(active_signals):
            with st.expander(f"{signal['category'].upper()}: {signal.get('trigger', {}).get('price', 'N/A')}"):
                st.json(signal)
    else:
        st.info(f"No active trading signals for {selected_ticker}")

    # Recent setups
    st.subheader("Recent Trading Setups")
    setups = fetch_api_data("setups", params={"limit": 5})
    if setups and "setups" in setups:
        for setup in setups["setups"]:
            with st.expander(f"{setup.get('date', 'Unknown')}: {setup.get('ticker_count', 0)} tickers"):
                st.json(setup)
    else:
        st.info("No recent trading setups available")

if __name__ == "__main__":
    main()