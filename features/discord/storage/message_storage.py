"""
Discord Message Storage

Stores and retrieves Discord messages for the trading application.
Maintains a history of messages in the PostgreSQL database.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import from common modules
from common.db import db
from common.db_models import DiscordMessageModel
from common.events.publisher import publish_discord_message
from common.events.constants import EventChannels

# Configure logging
logger = logging.getLogger(__name__)

def store_message(message_data):
    """
    Store Discord message in database.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        message = DiscordMessageModel(
            channel_id=message_data.get('channel_id', ''),
            message_id=message_data.get('message_id', ''),
            content=message_data.get('content', ''),
            author=message_data.get('author', '')
        )
        db.session.add(message)
        db.session.commit()

        # Publish event for other components
        publish_discord_message(message_data)
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
        message = DiscordMessageModel.query.order_by(
            DiscordMessageModel.created_at.desc()
        ).first()
        
        if message:
            return {
                'id': message.id,
                'content': message.content,
                'timestamp': message.created_at.isoformat() if message.created_at else None,
                'date': message.created_at.date().isoformat() if message.created_at else None,
                'author': message.author,
                'channel_id': message.channel_id,
                'message_id': message.message_id
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
        messages = DiscordMessageModel.query.order_by(
            DiscordMessageModel.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                'id': msg.id,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat() if msg.created_at else None,
                'date': msg.created_at.date().isoformat() if msg.created_at else None,
                'author': msg.author,
                'channel_id': msg.channel_id,
                'message_id': msg.message_id
            }
            for msg in messages
        ]
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
        return DiscordMessageModel.query.count()
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
        # Get message count
        count = get_message_count()
        
        # Get latest message
        latest = get_latest_message()
        
        stats = {
            "count": count,
            "latest_id": latest.get('id') if latest else None,
            "latest_timestamp": latest.get('timestamp') if latest else None,
            "latest_date": latest.get('date') if latest else None,
            "latest_author": latest.get('author') if latest else None,
            "latest_channel": latest.get('channel_id') if latest else None,
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
    except Exception as e:
        logger.error(f"Failed to get message stats: {e}")
        return {"count": 0, "ticker_frequency": {}}

# Command-line entry point for testing
if __name__ == "__main__":
    # Configure logging for command-line use
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
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