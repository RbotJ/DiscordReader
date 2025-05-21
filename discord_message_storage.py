"""
Discord Message Storage

Stores and retrieves Discord messages for the trading application.
Maintains a history of messages in the PostgreSQL database.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import database utilities
from db_utils import (store_discord_message, get_latest_message_from_database,
                      get_messages_from_database, get_message_stats_from_database)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def save_message(message_data: Dict[str, Any]) -> bool:
    """
    Save a Discord message to the database.
    Only saves authentic messages from Discord with valid ID and timestamp.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    # Verify this is an authentic message with required fields
    message_id = message_data.get('id')
    timestamp = message_data.get('timestamp')
    content = message_data.get('content')
    
    if not message_id or not timestamp or not content:
        logger.error("Message missing required fields (id, timestamp, or content)")
        return False
    
    # Store in database
    success = store_discord_message(message_data)
    
    if success:
        logger.info(f"Authentic message saved to database: {message_id}")
    else:
        logger.error(f"Failed to save message to database: {message_id}")
    
    return success

def get_latest_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest Discord message from the database.
    
    Returns:
        Dictionary containing message data or None if not found
    """
    message = get_latest_message_from_database()
    
    if message:
        # Reformat the message to match the expected structure
        return {
            'id': message.get('id'),
            'content': message.get('content'),
            'timestamp': message.get('created_at'),
            'date': message.get('date')
        }
    
    return None

def get_message_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get the message history from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries, newest first
    """
    return get_messages_from_database(limit=limit)

def get_message_count() -> int:
    """
    Get the total number of messages in the database.
    
    Returns:
        Integer count of messages
    """
    stats = get_message_stats_from_database()
    return stats.get('count', 0)

def get_message_stats() -> Dict[str, Any]:
    """
    Get statistics about stored messages from the database.
    
    Returns:
        Dictionary containing message statistics
    """
    # Get basic stats from database
    db_stats = get_message_stats_from_database()
    
    stats = {
        "count": db_stats.get('count', 0),
        "latest_id": db_stats.get('latest_id'),
        "latest_timestamp": db_stats.get('latest_timestamp'),
        "latest_date": db_stats.get('latest_date'),
        "ticker_frequency": {}  # We'll calculate this from message content
    }
    
    # Get message history to calculate ticker frequency
    messages = get_message_history(limit=100)
    
    if messages:
        # Calculate ticker frequency from message content
        ticker_counts = {}
        
        # Regular expression to find ticker symbols ($ followed by 1-5 uppercase letters)
        ticker_pattern = r'\$([A-Z]{1,5})'
        
        for message in messages:
            content = message.get('content', '')
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
    if stats.get('latest_id'):
        print(f"Latest message: {stats.get('latest_timestamp')}")
        print(f"Latest message ID: {stats.get('latest_id')}")
    
    # Print ticker frequency
    if stats.get('ticker_frequency'):
        print("\nTicker frequency:")
        for ticker, count in stats.get('ticker_frequency', {}).items():
            print(f"{ticker}: {count}")