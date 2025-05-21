#!/usr/bin/env python3
"""
Store Discord Messages in PostgreSQL Database

This script fetches Discord messages and stores them in the PostgreSQL database.
It serves as a verification tool for the Discord integration functionality.
"""
import os
import asyncio
import logging
import json
from datetime import datetime
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the message fetcher
import discord_message_fetcher

def store_message_in_database(message_data):
    """
    Store a Discord message in the PostgreSQL database.
    
    Args:
        message_data: Dictionary containing message data
        
    Returns:
        True if successful, False otherwise
    """
    if not message_data:
        logger.error("No message data to store")
        return False
        
    # Extract message details
    message_id = message_data.get('id')
    content = message_data.get('content')
    timestamp_str = message_data.get('timestamp')
    
    if not message_id or not content or not timestamp_str:
        logger.error("Message missing required fields (id, content, or timestamp)")
        return False
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine and connect to the database
        engine = create_engine(database_url)
        
        # Check if the setup_messages table exists
        with engine.connect() as conn:
            # Parse ISO timestamp to date
            message_date = datetime.fromisoformat(timestamp_str).date().isoformat()
            
            # Store message in setup_messages table
            query = text("""
                INSERT INTO setup_messages (id, date, raw_text, source, created_at)
                VALUES (:id, :date, :raw_text, 'discord', NOW())
                ON CONFLICT (id) DO UPDATE
                SET raw_text = :raw_text, date = :date, created_at = NOW()
            """)
            
            conn.execute(query, {
                'id': message_id,
                'date': message_date,
                'raw_text': content
            })
            conn.commit()
            
            logger.info(f"Successfully stored message {message_id} in database")
            
            # Now trigger processing of newly stored message
            # We'll publish an event to the event_bus table
            event_query = text("""
                INSERT INTO event_bus (event_type, payload, created_at)
                VALUES ('DISCORD_SETUP_MESSAGE_RECEIVED', :payload, NOW())
                RETURNING id
            """)
            
            payload = json.dumps({
                'message_id': message_id,
                'content': content,
                'timestamp': timestamp_str,
                'event_type': 'DISCORD_SETUP_MESSAGE_RECEIVED'
            })
            
            result = conn.execute(event_query, {'payload': payload})
            event_id = result.scalar()
            conn.commit()
            
            logger.info(f"Published message event with ID {event_id} to event bus")
            
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Database error storing message: {e}")
        return False
    except Exception as e:
        logger.error(f"Error storing message: {e}")
        return False

async def fetch_and_store_message():
    """
    Fetch the most recent Discord message and store it in the database.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Fetching Discord message...")
        message = await discord_message_fetcher.fetch_discord_message()
        
        if not message:
            logger.error("No message returned from fetcher")
            return False
        
        logger.info("Message fetched successfully, storing in database...")
        return store_message_in_database(message)
        
    except Exception as e:
        logger.error(f"Error in fetch and store process: {e}")
        return False

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
                    SELECT id, event_type, created_at
                    FROM event_bus
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                result = conn.execute(query)
                rows = result.fetchall()
                
                if rows:
                    print("\n===== RECENT EVENTS =====")
                    for row in rows:
                        print(f"Event ID: {row[0]}, Type: {row[1]}, Created: {row[2]}")
                    
        except Exception as e:
            print(f"Error checking ticker setups: {e}")
    else:
        print("\nFailed to store Discord message in database.")
        print("Please check logs for details.")

if __name__ == "__main__":
    main()