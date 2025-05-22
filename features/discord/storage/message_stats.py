"""
Discord Message Statistics Tool

This script displays statistics about stored Discord messages including 
counts and timestamps. It only uses authentic data received from Discord.
"""
import json
import logging
import os
from datetime import datetime

# Import our storage module (updated import path)
from features.discord.storage import message_storage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_message_stats():
    """
    Check and display message statistics.
    """
    # Get stats from storage
    stats = message_storage.get_message_stats()
    
    # Display general stats
    print("=== Discord Message Statistics ===")
    print(f"Total messages: {stats['count']}")
    
    if stats.get('latest_timestamp'):
        print(f"Latest message: {stats['latest_timestamp']}")
        print(f"Latest author: {stats.get('latest_author', 'Unknown')}")
        print(f"Latest channel: {stats.get('latest_channel', 'Unknown')}")
    else:
        print("No messages found in storage.")
    
    # Ticker frequency
    if stats.get('ticker_frequency'):
        print("\n=== Ticker Frequency ===")
        for ticker, count in stats['ticker_frequency'].items():
            print(f"${ticker}: {count} mention(s)")
    
    return stats

def display_message_content():
    """
    Display the content of the latest message.
    """
    latest = message_storage.get_latest_message()
    
    if latest and 'content' in latest:
        print("\n=== Latest Message Content ===")
        print(latest['content'])
    else:
        print("\nNo message content available.")

if __name__ == "__main__":
    # Check storage stats
    stats = check_message_stats()
    
    # Show latest message content
    if stats['count'] > 0:
        display_message_content()
    
    print("\nNote: This tool only displays authentic data received from Discord.")