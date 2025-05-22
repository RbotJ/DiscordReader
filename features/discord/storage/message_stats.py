"""
Discord Message Statistics

This module provides functions for retrieving and displaying statistics about
stored Discord messages including counts and timestamps.
"""
import json
import logging
from datetime import datetime

# Import from the new module location
from features.discord.storage.message_storage import get_message_stats, get_latest_message

# Create a logger for this module
logger = logging.getLogger(__name__)

def get_message_statistics():
    """
    Get message statistics.
    
    Returns:
        Dictionary containing message statistics
    """
    # Get stats from storage
    return get_message_stats()

def check_message_stats():
    """
    Check and display message statistics.
    
    Returns:
        Dictionary containing message statistics
    """
    # Get stats from storage
    stats = get_message_stats()
    
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
    
    Returns:
        Dictionary containing the latest message or None if not found
    """
    latest = get_latest_message()
    
    if latest and 'content' in latest:
        print("\n=== Latest Message Content ===")
        print(latest['content'])
        return latest
    else:
        print("\nNo message content available.")
        return None

# Command-line entry point
def main():
    """Command-line entry point for displaying message statistics."""
    # Configure logging for command-line use
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Check storage stats
    stats = check_message_stats()
    
    # Show latest message content
    if stats['count'] > 0:
        display_message_content()
    
    print("\nNote: This tool only displays authentic data received from Discord.")
    return 0

if __name__ == "__main__":
    main()