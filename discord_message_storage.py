"""
Discord Message Storage

Stores and retrieves Discord messages for the trading application.
Maintains a history of messages for analysis and display.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Storage file for message history
MESSAGE_HISTORY_FILE = "discord_message_history.json"
LATEST_MESSAGE_FILE = "latest_discord_message.json"

def save_message(message_data: Dict[str, Any]) -> bool:
    """
    Save a Discord message to the message history.
    Only saves authentic messages from Discord with valid ID and timestamp.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify this is an authentic message with required fields
        message_id = message_data.get('id')
        timestamp = message_data.get('timestamp')
        content = message_data.get('content')
        
        if not message_id or not timestamp or not content:
            logger.error("Message missing required fields (id, timestamp, or content)")
            return False
            
        # First, save as latest message
        with open(LATEST_MESSAGE_FILE, 'w') as f:
            json.dump(message_data, f, indent=2)
        
        # Then add to history
        history = get_message_history()
        if not history:
            history = []
        
        # Filter out any existing message with the same ID to avoid duplicates
        history = [msg for msg in history if msg.get('id') != message_id]
        
        # Add the new message at the beginning
        history.insert(0, message_data)
        
        # Limit history size (keep last 100 messages)
        MAX_HISTORY = 100
        if len(history) > MAX_HISTORY:
            history = history[:MAX_HISTORY]
        
        # Save the updated history
        with open(MESSAGE_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Authentic message added to history. Total messages: {len(history)}")
        return True
            
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return False

def get_latest_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest Discord message.
    
    Returns:
        Dictionary containing message data or None if not found
    """
    try:
        if os.path.exists(LATEST_MESSAGE_FILE):
            with open(LATEST_MESSAGE_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error reading latest message: {e}")
        return None

def get_message_history() -> List[Dict[str, Any]]:
    """
    Get the complete message history.
    
    Returns:
        List of message dictionaries, newest first
    """
    try:
        if os.path.exists(MESSAGE_HISTORY_FILE):
            with open(MESSAGE_HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error reading message history: {e}")
        return []

def get_message_count() -> int:
    """
    Get the total number of messages in the history.
    
    Returns:
        Integer count of messages
    """
    history = get_message_history()
    return len(history)

def get_message_stats() -> Dict[str, Any]:
    """
    Get statistics about stored messages.
    
    Returns:
        Dictionary containing message statistics
    """
    history = get_message_history()
    latest = get_latest_message()
    
    stats = {
        "count": len(history),
        "latest_timestamp": None,
        "latest_author": None,
        "latest_id": None,
        "latest_channel": None,
        "first_timestamp": None,
        "ticker_frequency": {}  # Track ticker frequency
    }
    
    if latest:
        stats["latest_timestamp"] = latest.get("timestamp")
        stats["latest_author"] = latest.get("author")
        stats["latest_id"] = latest.get("id")
        stats["latest_channel"] = latest.get("channel_name")
    
    if history and len(history) > 0:
        # The first item is the newest since we insert at the beginning
        first_msg = history[0]
        stats["first_timestamp"] = first_msg.get("timestamp")
        
        # Get the oldest message (last in the list)
        if len(history) > 1:
            oldest_msg = history[-1]
            stats["oldest_timestamp"] = oldest_msg.get("timestamp")
            
        # Calculate ticker frequency from message content
        ticker_counts = {}
        import re
        
        # Regular expression to find ticker symbols ($ followed by 1-5 uppercase letters)
        ticker_pattern = r'\$([A-Z]{1,5})'
        
        for message in history:
            content = message.get("content", "")
            tickers = re.findall(ticker_pattern, content)
            
            for ticker in tickers:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        # Sort by frequency (most frequent first)
        sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)
        stats["ticker_frequency"] = dict(sorted_tickers)
    
    return stats

if __name__ == "__main__":
    # Test the module
    stats = get_message_stats()
    print(f"Message count: {stats['count']}")
    if stats['latest_timestamp']:
        print(f"Latest message: {stats['latest_timestamp']} by {stats['latest_author']}")