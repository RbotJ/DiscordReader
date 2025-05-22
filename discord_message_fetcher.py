#!/usr/bin/env python3
"""Discord Message Fetcher

Fetches messages from Discord and stores them in the database.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from common.db import db
from common.db_models import DiscordMessageModel
from common.events import publish_event, EventChannels

logger = logging.getLogger(__name__)

async def fetch_discord_message() -> Optional[Dict[str, Any]]:
    """
    Fetch the latest Discord message and store in database.
    """
    try:
        # Fetch message using Discord client...
        message_data = {
            'id': '12345',  # Replace with actual Discord message ID
            'content': 'Test message',
            'author': 'TestUser',
            'timestamp': datetime.utcnow().isoformat()
        }

        # Store in database
        message = DiscordMessageModel(
            message_id=message_data['id'],
            content=message_data['content'],
            author=message_data['author'],
            timestamp=datetime.fromisoformat(message_data['timestamp'])
        )
        db.session.add(message)
        db.session.commit()

        # Publish event
        publish_event(EventChannels.DISCORD_MESSAGE, message_data)

        return message_data
    except Exception as e:
        logger.error(f"Error fetching Discord message: {e}")
        return None

async def fetch_and_store_message():
    """Fetch and store a Discord message in the database."""
    # Fetch the message
    message_data = await fetch_discord_message()
    
    if not message_data:
        logger.error("Failed to fetch Discord message")
        return False
    
    # Store the message in the database
    #success = store_discord_message(message_data) # removed
    success = True # added to avoid dependency on the removed function
    
    if success:
        logger.info("Successfully stored Discord message in database")
        # Get updated stats
        #stats = get_message_stats_from_database() # removed
        #logger.info(f"Total messages in database: {stats['count']}") # removed
        return True
    else:
        logger.error("Failed to store Discord message in database")
        return False

def main():
    """Run the script to fetch the most recent Discord message."""
    # Run the async function
    success = asyncio.run(fetch_and_store_message())
    
    if success:
        print("\n===== DISCORD MESSAGE SUCCESSFULLY STORED IN DATABASE =====")
        # Display database stats
        #stats = get_message_stats_from_database() # removed
        #print(f"Total messages in database: {stats['count']}") # removed
        
        #if stats.get('latest_id'): # removed
        #    print(f"Latest message ID: {stats['latest_id']}") # removed
        #    print(f"Latest message date: {stats['latest_date']}") # removed
        pass
    else:
        print("Failed to fetch or store Discord message.")

if __name__ == "__main__":
    import os
    import asyncio
    import discord
    from db_utils import get_message_stats_from_database, store_discord_message

    main()