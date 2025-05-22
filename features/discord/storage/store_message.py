#!/usr/bin/env python3
"""
Store Discord Message

A module to fetch the most recent message from the A+ Trading Discord channel
and store it in the PostgreSQL database.
"""
import os
import asyncio
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

# Import from our refactored structure
from features.discord.storage.message_storage import store_message
from common.events.publisher import publish_discord_message, publish_discord_setup

# Configure logging
logger = logging.getLogger(__name__)

async def fetch_discord_message():
    """
    Fetch a Discord message.
    
    This is a placeholder that would be implemented in the Discord client.
    For now, it returns a mock message for testing purposes.
    
    Returns:
        Dictionary containing message data or None if failed
    """
    try:
        # Here you would actually call the Discord API
        # This is just a placeholder for testing the storage mechanism
        return {
            'channel_id': os.environ.get('DISCORD_CHANNEL_ID', '123456789'),
            'message_id': 'test_message_id',
            'content': 'This is a test message from the store_message module.',
            'author': 'Test User',
        }
    except Exception as e:
        logger.error(f"Failed to fetch Discord message: {e}")
        return None

async def fetch_and_store_message():
    """
    Fetch and store a Discord message in the database.
    
    Returns:
        True if successful, False otherwise
    """
    # Fetch the message
    message_data = await fetch_discord_message()
    
    if not message_data:
        logger.error("Failed to fetch Discord message")
        return False
    
    # Store the message in the database
    success = store_message(message_data)
    
    if not success:
        logger.error("Failed to store Discord message in database")
        return False
    
    # Publish the message as an event
    event_success = publish_discord_message(message_data)
    
    if event_success:
        logger.info("Published Discord message as an event")
    else:
        logger.warning("Failed to publish Discord message as an event")
    
    # Check if this is a trading setup message and publish it separately
    # A simple heuristic: look for common trading terms
    content = message_data.get('content', '').lower()
    setup_keywords = ['setup', 'breakout', 'trade', 'long', 'short', 'trigger', 'buy', 'sell', 'entry', 'target']
    
    is_setup = any(keyword in content for keyword in setup_keywords)
    
    if is_setup:
        setup_success = publish_discord_setup(message_data)
        if setup_success:
            logger.info("Published Discord message as a trading setup")
        else:
            logger.warning("Failed to publish Discord message as a trading setup")
    
    return success

def check_database_for_setups():
    """
    Check the database for recent ticker setups.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        database_url = os.environ.get('DATABASE_URL')
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if any ticker setups were created
            query = text("""
                SELECT s.ticker, ts.entry_price, ts.created_at, COUNT(s.id) AS total_signals
                FROM ticker_setups ts
                JOIN setups s ON ts.setup_id = s.id
                GROUP BY s.ticker, ts.entry_price, ts.created_at
                ORDER BY ts.created_at DESC
                LIMIT 5
            """)
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            if rows:
                print("\n===== RECENT TICKER SETUPS =====")
                for row in rows:
                    print(f"Ticker: {row[0]}, Entry: ${row[1]:.2f}, Created: {row[2]}, Signals: {row[3]}")
            else:
                print("\nNo ticker setups found in database. Message may still be in processing queue.")
        
        # Also check the events table
        with engine.connect() as conn:
            query = text("""
                SELECT id, channel, created_at 
                FROM events 
                ORDER BY id DESC 
                LIMIT 5
            """)
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            if rows:
                print("\n===== RECENT EVENTS =====")
                for row in rows:
                    print(f"ID: {row[0]}, Channel: {row[1]}, Created: {row[2]}")
            else:
                print("\nNo events found in the events table.")
                
        return True
    except Exception as e:
        print(f"Error checking database after message storage: {e}")
        return False

# Command-line entry point
def main():
    """
    Command-line entry point for fetching and storing Discord messages.
    
    Returns:
        0 if successful, 1 otherwise
    """
    # Configure logging for command-line use
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run the async function
    success = asyncio.run(fetch_and_store_message())
    
    if success:
        print("\n===== MESSAGE SUCCESSFULLY STORED IN DATABASE =====")
        # Now check if the message was properly processed
        check_database_for_setups()
        return 0
    else:
        print("Failed to fetch or store Discord message.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())