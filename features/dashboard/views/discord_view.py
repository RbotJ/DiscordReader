"""
Discord Stats View

This module provides a dashboard view for Discord message statistics and visualizations.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import json
import logging
from typing import Dict, Any, List, Optional

# Import components
from ..components.table_component import create_data_table, create_stats_table, create_expandable_table
from ..components.chart_component import display_chart, create_performance_chart

# Setup logging
logger = logging.getLogger(__name__)

# API base URL - Flask backend
API_BASE_URL = "http://localhost:5000/api"

# Data retrieval functions
def get_discord_stats():
    """Get Discord message statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard/data/discord-stats")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch Discord stats: {response.status_code}")
            return {}
    except Exception as e:
        st.error(f"Error fetching Discord stats: {str(e)}")
        return {}

def format_timestamp(timestamp_str):
    """Format ISO timestamp to readable date/time"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return timestamp_str

def create_message_count_chart(messages_by_date):
    """Create a chart showing message counts by date"""
    if not messages_by_date:
        # Create an empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title="Message Count by Date - No Data Available",
            height=300
        )
        return fig
    
    # Convert to DataFrame for plotting
    df = pd.DataFrame([
        {"Date": date, "Count": count}
        for date, count in messages_by_date.items()
    ])
    
    # Sort by date
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Create the figure
    fig = px.bar(
        df, 
        x='Date', 
        y='Count',
        title='Message Count by Date'
    )
    
    # Style adjustments
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#444')
    )
    
    return fig

def create_ticker_frequency_chart(ticker_counts):
    """Create a chart showing ticker frequency"""
    if not ticker_counts:
        # Create an empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title="Ticker Frequency - No Data Available",
            height=300
        )
        return fig
    
    # Convert to DataFrame for plotting
    df = pd.DataFrame([
        {"Ticker": ticker, "Count": count}
        for ticker, count in ticker_counts.items()
    ])
    
    # Sort by count descending
    df = df.sort_values('Count', ascending=False).head(15)  # Top 15 tickers
    
    # Create the figure
    fig = px.bar(
        df, 
        x='Ticker', 
        y='Count',
        title='Most Mentioned Tickers'
    )
    
    # Style adjustments
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#444')
    )
    
    return fig

def render():
    """Render the Discord stats dashboard view"""
    # Get Discord stats data
    discord_data = get_discord_stats()
    
    if not discord_data:
        st.info("Discord statistics data is not available. Please check your API connection.")
        return
    
    # Extract data components
    stats = discord_data.get('stats', {})
    recent_messages = discord_data.get('recent_messages', [])
    
    # Display summary statistics
    st.subheader("Discord Message Statistics")
    
    if stats:
        # Create metrics from stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Total Messages", 
                value=stats.get('total_messages', 0)
            )
        
        with col2:
            st.metric(
                label="Messages Today", 
                value=stats.get('messages_today', 0)
            )
        
        with col3:
            st.metric(
                label="Active Tickers", 
                value=len(stats.get('ticker_counts', {}))
            )
        
        # Extract time-based statistics
        messages_by_date = stats.get('messages_by_date', {})
        
        # Display message count chart
        if messages_by_date:
            st.subheader("Message Activity")
            message_chart = create_message_count_chart(messages_by_date)
            st.plotly_chart(message_chart, use_container_width=True)
        
        # Display ticker frequency chart
        ticker_counts = stats.get('ticker_counts', {})
        if ticker_counts:
            st.subheader("Ticker Mentions")
            ticker_chart = create_ticker_frequency_chart(ticker_counts)
            st.plotly_chart(ticker_chart, use_container_width=True)
    else:
        st.info("No Discord statistics available")
    
    # Display recent messages
    st.subheader("Recent Discord Messages")
    
    if recent_messages:
        # Convert to DataFrame for display
        messages_df = pd.DataFrame(recent_messages)
        
        # Format timestamps
        if 'timestamp' in messages_df.columns:
            messages_df['formatted_time'] = messages_df['timestamp'].apply(format_timestamp)
        
        # Select columns to display
        display_columns = ['formatted_time', 'author', 'content']
        if set(display_columns).issubset(messages_df.columns):
            display_df = messages_df[display_columns].copy()
            display_df.columns = ['Time', 'Author', 'Message']
            
            # Display messages table
            create_data_table(display_df)
        else:
            st.info("Message data is in an unexpected format")
    else:
        st.info("No recent messages available")
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")