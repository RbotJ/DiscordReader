#!/usr/bin/env python3
"""
Store Discord Message

A script to fetch the most recent message from the A+ Trading Discord channel
and store it in the PostgreSQL database.
"""
import os
import asyncio
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

# Import our local modules
from features.discord import discord_message_fetcher
from common.db.utils import store_discord_message
from common.events.publisher import publish_discord_message, publish_discord_setup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_and_store_message():
    """Fetch and store a Discord message in the database."""
    # Fetch the message
    message_data = await discord_message_fetcher.fetch_discord_message()
    
    if not message_data:
        logger.error("Failed to fetch Discord message")
        return False
    
    # Store the message in the database
    success = store_discord_message(message_data)
    
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

def main():
    """Run the script to fetch and store the most recent Discord message."""
    # Run the async function
    success = asyncio.run(fetch_and_store_message())
    
    if success:
        print("\n===== MESSAGE SUCCESSFULLY STORED IN DATABASE =====")
        # Now check if the message was properly processed by querying ticker setups
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
            
            # Also check the event_bus table
            with engine.connect() as conn:
                query = text("""
                    SELECT id, event_type, channel, created_at 
                    FROM event_bus 
                    ORDER BY id DESC 
                    LIMIT 5
                """)
                
                result = conn.execute(query)
                rows = result.fetchall()
                
                if rows:
                    print("\n===== RECENT EVENTS =====")
                    for row in rows:
                        print(f"ID: {row[0]}, Type: {row[1]}, Channel: {row[2]}, Created: {row[3]}")
                else:
                    print("\nNo events found in the event_bus table.")
                    
        except Exception as e:
            print(f"Error checking database after message storage: {e}")
    else:
        print("Failed to fetch or store Discord message.")

if __name__ == "__main__":
    main()