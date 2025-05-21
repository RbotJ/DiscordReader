"""
Daily Trading Ticker Dashboard

Displays today's date, today's active tickers from Discord messages,
and "Awaiting Trade Theory" if no messages have been received today.
"""
import streamlit as st
import json
import os
from datetime import datetime, date

# Storage file for message history
MESSAGE_HISTORY_FILE = "discord_message_history.json"

def load_message_history():
    """Load the message history from file"""
    if os.path.exists(MESSAGE_HISTORY_FILE):
        try:
            with open(MESSAGE_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading message history: {e}")
    return []

def get_todays_tickers():
    """Get tickers from today's messages only"""
    messages = load_message_history()
    today = date.today().isoformat()
    todays_messages = []
    
    for message in messages:
        timestamp = message.get("timestamp", "")
        if timestamp and timestamp.startswith(today):
            todays_messages.append(message)
    
    # Extract tickers using regex
    import re
    ticker_pattern = r'\$([A-Z]{1,5})'
    tickers = set()
    
    for message in todays_messages:
        content = message.get("content", "")
        found_tickers = re.findall(ticker_pattern, content)
        tickers.update(found_tickers)
    
    return list(tickers), len(todays_messages)

def main():
    """Main dashboard function"""
    # Set page configuration
    st.set_page_config(
        page_title="Today's Trading Tickers",
        page_icon="📈",
        layout="wide"
    )
    
    # Get today's date and display it prominently
    today = date.today()
    st.title(f"Trading Dashboard - {today.strftime('%A, %B %d, %Y')}")
    
    # Get today's tickers
    todays_tickers, message_count = get_todays_tickers()
    
    # Display today's tickers or "Awaiting Trade Theory"
    st.header("Today's Active Tickers")
    
    # Create columns for ticker display
    if todays_tickers:
        cols = st.columns(len(todays_tickers) if len(todays_tickers) <= 6 else 6)
        
        for i, ticker in enumerate(todays_tickers):
            col_index = i % 6  # Wrap to next row after 6 columns
            with cols[col_index]:
                st.metric(label=f"${ticker}", value="Active")
        
        st.success(f"Found {message_count} authentic trading message(s) from today with {len(todays_tickers)} active ticker(s)")
    
    # Additional information section
    with st.expander("Recent Message History"):
        st.write("Last 5 messages received (any date):")
        messages = load_message_history()[:5]  # Get the 5 most recent messages
        
        for i, message in enumerate(messages):
            timestamp = message.get("timestamp", "")
            author = message.get("author", "Unknown")
            channel = message.get("channel_name", "Unknown")
            content = message.get("content", "No content")
            
            formatted_date = "Unknown date"
            try:
                msg_datetime = datetime.fromisoformat(timestamp)
                formatted_date = msg_datetime.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
            
            st.markdown(f"**Message {i+1}** - {formatted_date} by {author} in {channel}")
            st.text(content)
            st.markdown("---")

if __name__ == "__main__":
    main()