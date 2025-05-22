"""
Daily Ticker View

This module provides a dashboard view for daily active tickers.
Integrated from the original daily_ticker_dashboard.py.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any

# Import components
from ..components.table_component import create_data_table, create_metrics_row

# Setup logging
logger = logging.getLogger(__name__)

def get_active_tickers() -> List[str]:
    """Get active tickers from database"""
    try:
        from common.db import db
        from common.db_models import TickerDataModel
        
        today = datetime.utcnow().date()
        ticker_data = TickerDataModel.query.filter(
            TickerDataModel.date >= today
        ).all()
        return [t.symbol for t in ticker_data]
    except Exception as e:
        logger.error(f"Error getting active tickers: {e}")
        st.error(f"Database error: {e}")
        return []

def get_ticker_performance(tickers: List[str]) -> pd.DataFrame:
    """Get performance data for tickers"""
    try:
        from common.db import db
        from common.db_models import TickerDataModel
        
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        performance_data = []
        
        for ticker in tickers:
            # Get today's data
            today_data = TickerDataModel.query.filter(
                TickerDataModel.symbol == ticker,
                TickerDataModel.date == today
            ).first()
            
            # Get yesterday's data
            yesterday_data = TickerDataModel.query.filter(
                TickerDataModel.symbol == ticker,
                TickerDataModel.date == yesterday
            ).first()
            
            if today_data:
                change = 0
                change_percent = 0
                
                if yesterday_data and yesterday_data.close > 0:
                    change = today_data.close - yesterday_data.close
                    change_percent = (change / yesterday_data.close) * 100
                
                performance_data.append({
                    'Ticker': ticker,
                    'Open': today_data.open,
                    'High': today_data.high,
                    'Low': today_data.low,
                    'Close': today_data.close,
                    'Volume': today_data.volume,
                    'Change': change,
                    'Change %': change_percent
                })
        
        return pd.DataFrame(performance_data)
    except Exception as e:
        logger.error(f"Error getting ticker performance: {e}")
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def get_recent_events() -> List[Dict[str, Any]]:
    """Get recent ticker-related events"""
    try:
        from common.events import get_latest_events, EventChannels
        
        events = get_latest_events(channel=EventChannels.TICKER_DATA, limit=20)
        return events
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        return []

def render():
    """Render the daily tickers dashboard view"""
    st.title("Daily Active Tickers")
    
    # Get active tickers
    tickers = get_active_tickers()
    
    if not tickers:
        st.warning("No active tickers found for today")
        return
    
    # Display metrics
    metrics = [
        {
            'label': 'Active Tickers',
            'value': len(tickers)
        },
        {
            'label': 'Date',
            'value': datetime.utcnow().strftime("%Y-%m-%d")
        }
    ]
    
    create_metrics_row(metrics)
    
    # Display ticker list
    st.subheader("Active Tickers")
    tickers_df = pd.DataFrame({"Ticker": tickers})
    create_data_table(tickers_df)
    
    # Get and display performance data
    st.subheader("Ticker Performance")
    performance_df = get_ticker_performance(tickers)
    
    if not performance_df.empty:
        # Format the performance data
        formatting = {
            'Open': lambda x: f"${x:.2f}",
            'High': lambda x: f"${x:.2f}",
            'Low': lambda x: f"${x:.2f}",
            'Close': lambda x: f"${x:.2f}",
            'Volume': lambda x: f"{x:,.0f}",
            'Change': lambda x: f"${x:.2f}",
            'Change %': lambda x: f"{x:.2f}%"
        }
        
        create_data_table(performance_df, formatting=formatting)
    else:
        st.info("No performance data available for today's tickers")
    
    # Display recent events
    st.subheader("Recent Ticker Events")
    events = get_recent_events()
    
    if events:
        events_df = pd.DataFrame(events)
        if 'timestamp' in events_df.columns:
            events_df['formatted_time'] = pd.to_datetime(events_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Select columns to display
        display_columns = ['formatted_time', 'symbol', 'event_type', 'data']
        if set(display_columns).issubset(events_df.columns):
            display_df = events_df[display_columns].copy()
            create_data_table(display_df)
        else:
            st.dataframe(events_df)
    else:
        st.info("No recent ticker events")
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")