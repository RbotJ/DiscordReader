"""
Discord Statistics Dashboard

This dashboard displays statistics about Discord messages, including message count and
timestamps from the latest messages. It also shows a visualization of recent trading setups.
"""
import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="Discord Message Stats",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File paths for message data
MESSAGE_HISTORY_FILE = "discord_message_history.json"
LATEST_MESSAGE_FILE = "latest_discord_message.json"
PARSED_SETUP_FILE = "parsed_setups.json"

def load_message_history():
    """Load the message history from file"""
    if os.path.exists(MESSAGE_HISTORY_FILE):
        try:
            with open(MESSAGE_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading message history: {e}")
    return []

def load_latest_message():
    """Load the latest message from file"""
    if os.path.exists(LATEST_MESSAGE_FILE):
        try:
            with open(LATEST_MESSAGE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading latest message: {e}")
    return None

def load_parsed_setup():
    """Load the parsed setup from file"""
    if os.path.exists(PARSED_SETUP_FILE):
        try:
            with open(PARSED_SETUP_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading parsed setup: {e}")
    return None

def format_timestamp(timestamp_str):
    """Format ISO timestamp to readable date/time"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

def main():
    """Main dashboard function"""
    st.title("Discord Message Statistics")
    
    # Load data
    message_history = load_message_history()
    latest_message = load_latest_message()
    parsed_setup = load_parsed_setup()
    
    # Summary metrics
    st.header("Message Summary")
    
    cols = st.columns(3)
    
    with cols[0]:
        st.metric("Total Messages", len(message_history))
    
    with cols[1]:
        if latest_message and "timestamp" in latest_message:
            st.metric("Latest Message", format_timestamp(latest_message["timestamp"]))
        else:
            st.metric("Latest Message", "N/A")
    
    with cols[2]:
        if latest_message and "author" in latest_message:
            st.metric("Latest Author", latest_message.get("author", "Unknown"))
        else:
            st.metric("Latest Author", "N/A")
    
    # Latest message content
    st.header("Latest Discord Message")
    
    if latest_message:
        expander = st.expander("View Latest Message Content", expanded=True)
        with expander:
            for key, value in latest_message.items():
                if key == "content":
                    st.markdown("### Message Content:")
                    st.code(value)
                elif key != "id":  # Skip the id field
                    st.markdown(f"**{key.capitalize()}**: {value}")
    else:
        st.info("No Discord messages found. Try generating sample data with `python generate_sample_discord_data.py`")
    
    # Latest parsed setup
    st.header("Latest Parsed Trading Setup")
    
    if parsed_setup:
        tab1, tab2 = st.tabs(["Trading Data", "Raw JSON"])
        
        with tab1:
            # Primary ticker and signals
            cols = st.columns(3)
            
            with cols[0]:
                st.markdown(f"**Primary Ticker**: {parsed_setup.get('primary_ticker', 'N/A')}")
                st.markdown(f"**Signal Type**: {parsed_setup.get('signal_type', 'N/A')}")
                st.markdown(f"**Bias**: {parsed_setup.get('bias', 'N/A')}")
            
            with cols[1]:
                st.markdown("**Tickers:**")
                for ticker in parsed_setup.get('tickers', []):
                    st.markdown(f"- {ticker}")
            
            with cols[2]:
                confidence = parsed_setup.get('confidence', 0)
                st.progress(confidence, text=f"Confidence: {confidence*100:.0f}%")
            
            # Display the raw message
            st.markdown("### Original Message:")
            st.code(parsed_setup.get('raw_message', 'No message available'))
            
            # Ticker-specific data
            st.markdown("### Ticker-Specific Data:")
            
            ticker_data = parsed_setup.get('ticker_specific_data', {})
            if ticker_data:
                for ticker, data in ticker_data.items():
                    with st.expander(f"{ticker} Details", expanded=ticker == parsed_setup.get('primary_ticker')):
                        st.markdown(f"**Signal**: {data.get('signal_type', 'N/A')}")
                        st.markdown(f"**Bias**: {data.get('bias', 'N/A')}")
                        
                        # Price levels
                        if data.get('support_levels'):
                            st.markdown(f"**Support Levels**: {', '.join([str(x) for x in data['support_levels']])}")
                        if data.get('resistance_levels'):
                            st.markdown(f"**Resistance Levels**: {', '.join([str(x) for x in data['resistance_levels']])}")
                        if data.get('target_levels'):
                            st.markdown(f"**Target Levels**: {', '.join([str(x) for x in data['target_levels']])}")
                        if data.get('stop_levels'):
                            st.markdown(f"**Stop Levels**: {', '.join([str(x) for x in data['stop_levels']])}")
            else:
                st.info("No ticker-specific data available")
        
        with tab2:
            st.json(parsed_setup)
    else:
        st.info("No parsed setup data found")
    
    # Message history visualization
    st.header("Message History")
    
    if message_history:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(message_history)
        
        # Extract datetime from timestamp strings
        df['datetime'] = pd.to_datetime(df['timestamp'])
        
        # Sort by datetime
        df = df.sort_values('datetime')
        
        # Add a column for message index (count)
        df['message_index'] = range(1, len(df) + 1)
        
        # Create a timeline visualization
        fig = px.scatter(
            df,
            x='datetime',
            y='message_index',
            hover_data=['author', 'channel_name'],
            labels={'datetime': 'Time', 'message_index': 'Message Count'},
            title='Discord Message Timeline'
        )
        
        # Increase marker size
        fig.update_traces(marker=dict(size=12))
        
        # Layout improvements
        fig.update_layout(
            height=500,
            xaxis_title="Message Time",
            yaxis_title="Message Count",
            hovermode="closest"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show message table
        with st.expander("View Message History Table", expanded=False):
            # Format the datetime column for display
            df['formatted_time'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Select and reorder columns for display
            display_df = df[['message_index', 'formatted_time', 'author', 'channel_name']]
            display_df.columns = ['#', 'Time', 'Author', 'Channel']
            
            st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No message history found. Try generating sample data with `python generate_sample_discord_data.py`")

if __name__ == "__main__":
    main()