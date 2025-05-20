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
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First, save as latest message
        with open(LATEST_MESSAGE_FILE, 'w') as f:
            json.dump(message_data, f, indent=2)
        
        # Then add to history
        history = get_message_history()
        if not history:
            history = []
        
        # Add the current message if it's not already in the history
        # Check by message ID to avoid duplicates
        message_id = message_data.get('id')
        if message_id:
            # Filter out any existing message with the same ID
            history = [msg for msg in history if msg.get('id') != message_id]
            
            # Add the new message at the beginning
            history.insert(0, message_data)
            
            # Limit history size if needed (e.g., keep last 100 messages)
            MAX_HISTORY = 100
            if len(history) > MAX_HISTORY:
                history = history[:MAX_HISTORY]
            
            # Save the updated history
            with open(MESSAGE_HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"Message added to history. Total messages: {len(history)}")
            return True
        else:
            logger.error("Message data does not contain an ID")
            return False
            
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
        "first_timestamp": None
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
    
    return stats

if __name__ == "__main__":
    # Test the module
    stats = get_message_stats()
    print(f"Message count: {stats['count']}")
    if stats['latest_timestamp']:
        print(f"Latest message: {stats['latest_timestamp']} by {stats['latest_author']}")