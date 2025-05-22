"""
Simple Dashboard View

This module provides a simple dashboard view using PostgreSQL data.
Integrated from the original simple_dashboard.py.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List

# Import components
from ..components.table_component import create_data_table

# Setup logging
logger = logging.getLogger(__name__)

def load_recent_messages() -> pd.DataFrame:
    """Load recent Discord messages from database"""
    try:
        from common.db import db
        from common.db_models import DiscordMessageModel
        
        messages = DiscordMessageModel.query.order_by(
            DiscordMessageModel.timestamp.desc()
        ).limit(100).all()

        return pd.DataFrame([{
            'id': msg.message_id,
            'content': msg.content,
            'author': msg.author,
            'timestamp': msg.timestamp
        } for msg in messages])
    except Exception as e:
        logger.error(f"Error loading recent messages: {e}")
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def load_recent_setups() -> pd.DataFrame:
    """Load recent trading setups from database"""
    try:
        from common.db import db
        from common.db_models import SetupModel
        
        setups = SetupModel.query.order_by(
            SetupModel.timestamp.desc()
        ).limit(50).all()

        return pd.DataFrame([{
            'id': setup.id,
            'ticker': setup.ticker,
            'type': setup.setup_type,
            'price': setup.price,
            'timestamp': setup.timestamp
        } for setup in setups])
    except Exception as e:
        logger.error(f"Error loading recent setups: {e}")
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def render():
    """Render the simple dashboard view"""
    st.title('A+ Trading Simple Monitor')
    
    # Create tabs for different data views
    tab1, tab2 = st.tabs(["Discord Messages", "Trading Setups"])
    
    with tab1:
        # Load and display recent messages
        st.subheader('Recent Discord Messages')
        messages_df = load_recent_messages()
        
        if not messages_df.empty:
            # Format timestamps
            if 'timestamp' in messages_df.columns:
                messages_df['formatted_time'] = pd.to_datetime(messages_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                display_df = messages_df[['formatted_time', 'author', 'content']].copy()
                display_df.columns = ['Time', 'Author', 'Message']
                create_data_table(display_df)
            else:
                create_data_table(messages_df)
        else:
            st.info('No recent messages found')
    
    with tab2:
        # Load and display recent setups
        st.subheader('Recent Trading Setups')
        setups_df = load_recent_setups()
        
        if not setups_df.empty:
            # Format timestamps and other data
            if 'timestamp' in setups_df.columns:
                setups_df['formatted_time'] = pd.to_datetime(setups_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Format price
            if 'price' in setups_df.columns:
                setups_df['formatted_price'] = setups_df['price'].apply(lambda x: f"${x:.2f}" if x else "N/A")
            
            # Select columns for display
            display_columns = ['formatted_time', 'ticker', 'type', 'formatted_price']
            if set(display_columns).issubset(setups_df.columns):
                display_df = setups_df[display_columns].copy()
                display_df.columns = ['Time', 'Ticker', 'Setup Type', 'Price']
                create_data_table(display_df)
            else:
                create_data_table(setups_df)
        else:
            st.info('No recent setups found')
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")