"""
Discord Message Storage and Stats

This module provides functionality for storing Discord messages
and retrieving statistics about them from the database.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from common.db import db
from common.db_models import DiscordMessageModel
from common.events import publish_event, EventChannels

# Configure logging
logger = logging.getLogger(__name__)

def store_message(message_data: Dict[str, Any]) -> bool:
    """
    Store a Discord message in the database.
    
    Args:
        message_data: Dictionary containing message data
            Required keys: channel_id, message_id, content, author
            
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create message using keyword arguments
        message = DiscordMessageModel()
        message.channel_id = message_data['channel_id']
        message.message_id = message_data['message_id']
        message.content = message_data['content']
        message.author = message_data.get('author', 'Unknown')
        message.created_at = datetime.utcnow()
        db.session.add(message)
        db.session.commit()

        # Publish event for other components
        publish_event(EventChannels.DISCORD_SETUP_MESSAGE, message_data)
        logger.info(f"Stored Discord message {message_data['message_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to store Discord message: {e}")
        db.session.rollback()
        return False

def get_latest_message() -> Optional[Dict[str, Any]]:
    """
    Get the latest Discord message from the database.
    
    Returns:
        Dictionary containing message data or None if not found
    """
    try:
        message = db.session.query(DiscordMessageModel).order_by(
            DiscordMessageModel.created_at.desc()
        ).first()
        
        if message:
            return {
                'id': message.id,
                'message_id': message.message_id,
                'channel_id': message.channel_id,
                'content': message.content,
                'author': message.author,
                'created_at': message.created_at.isoformat() if message.created_at else None
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get latest message: {e}")
        return None

def get_message_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get the message history from the database.
    
    Args:
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of message dictionaries, newest first
    """
    try:
        messages = db.session.query(DiscordMessageModel).order_by(
            DiscordMessageModel.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for message in messages:
            result.append({
                'id': message.id,
                'message_id': message.message_id,
                'channel_id': message.channel_id,
                'content': message.content,
                'author': message.author,
                'created_at': message.created_at.isoformat() if message.created_at else None
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get message history: {e}")
        return []

def get_message_count() -> int:
    """
    Get the total number of messages in the database.
    
    Returns:
        Integer count of messages
    """
    try:
        return db.session.query(DiscordMessageModel).count()
    except Exception as e:
        logger.error(f"Failed to get message count: {e}")
        return 0

def get_message_stats() -> Dict[str, Any]:
    """
    Get statistics about stored messages from the database.
    
    Returns:
        Dictionary containing message statistics
    """
    try:
        # Get count of messages
        count = get_message_count()
        
        # Get latest message
        latest = get_latest_message()
        
        # Extract tickers from messages
        ticker_frequency = {}
        messages = get_message_history(limit=100)
        
        # Regex for tickers ($ followed by 1-5 uppercase letters)
        ticker_pattern = r'\$([A-Z]{1,5})'
        
        for message in messages:
            content = message.get('content', '')
            found_tickers = re.findall(ticker_pattern, content)
            
            for ticker in found_tickers:
                if ticker in ticker_frequency:
                    ticker_frequency[ticker] += 1
                else:
                    ticker_frequency[ticker] = 1
        
        # Sort by frequency, descending
        ticker_frequency = dict(sorted(
            ticker_frequency.items(), 
            key=lambda item: item[1], 
            reverse=True
        ))
        
        # Build stats dictionary
        stats = {
            'count': count,
            'ticker_frequency': ticker_frequency
        }
        
        if latest:
            stats.update({
                'latest_id': latest.get('id'),
                'latest_message_id': latest.get('message_id'),
                'latest_timestamp': latest.get('created_at'),
                'latest_author': latest.get('author'),
                'latest_channel': latest.get('channel_id')
            })
            
        return stats
    except Exception as e:
        logger.error(f"Failed to get message stats: {e}")
        return {'count': 0}

def display_message_stats():
    """
    Display statistics about stored Discord messages.
    
    Returns:
        Dict containing the statistics that were displayed
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
        The message that was displayed, or None if no message was found
    """
    latest = get_latest_message()
    
    if latest and 'content' in latest:
        print("\n=== Latest Message Content ===")
        print(latest['content'])
        return latest
    else:
        print("\nNo message content available.")
        return None

if __name__ == "__main__":
    # Check storage stats
    stats = display_message_stats()
    
    # Show latest message content
    if stats['count'] > 0:
        display_message_content()
    
    print("\nNote: This tool only displays authentic data received from Discord.")