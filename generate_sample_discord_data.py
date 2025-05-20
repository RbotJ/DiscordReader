"""
Generate Sample Discord Data for Testing

This script generates sample Discord message data for testing the
trade monitor dashboard without requiring a Discord connection.
"""
import json
import logging
import os
from datetime import datetime, timedelta
import random

# Import our storage module
import discord_message_storage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample Discord messages
SAMPLE_MESSAGES = [
    """
A+ Trade Setups - Today May 20

$SPY Rejection Near 586
Bias: Bearish

$AAPL Breaking Support
Support at $182
Target: $178
Stop: $185
    """,
    """
A+ Trade Setups - Today's Picks

$NVDA Bounce at $920
Looks strong heading into earnings next week
    """,
    """
A+ Trade Setups - Hot Alert

$AMD Breaking Out Above $143
Target: $150
Stop: $140
Resistance at $147
    """,
    """
A+ Trade Setups - Sector Alert

$META Support Test at $450
Looking for bounce
Target: $470
Stop: $440
    """,
    """
A+ Trade Setups - Quick Update

$TSLA Breakdown Below $180
Bias: Bearish
Support at $170
    """
]

def generate_sample_messages(count=5):
    """
    Generate sample Discord messages.
    
    Args:
        count: Number of messages to generate
        
    Returns:
        List of generated message dictionaries
    """
    messages = []
    
    # Base timestamp (now)
    base_time = datetime.now()
    
    for i in range(count):
        # Message timestamp (going backward in time from now)
        msg_time = base_time - timedelta(hours=i*4)
        
        # Select a random message content
        content = SAMPLE_MESSAGES[i % len(SAMPLE_MESSAGES)]
        
        # Generate a random message ID
        msg_id = str(random.randint(1000000000000000000, 9999999999999999999))
        
        # Create the message data
        message_data = {
            "id": msg_id,
            "content": content,
            "author": "TradingBot",
            "timestamp": msg_time.isoformat(),
            "channel_name": "a-plus-signals",
            "fetch_timestamp": datetime.now().isoformat()
        }
        
        messages.append(message_data)
    
    return messages

def save_sample_messages(count=5):
    """
    Generate and save sample messages to storage.
    
    Args:
        count: Number of messages to generate
        
    Returns:
        Number of messages saved successfully
    """
    messages = generate_sample_messages(count)
    
    success_count = 0
    for message in messages:
        if discord_message_storage.save_message(message):
            success_count += 1
    
    logger.info(f"Generated and saved {success_count} sample messages")
    
    # Get updated stats
    stats = discord_message_storage.get_message_stats()
    logger.info(f"Total messages in storage: {stats['count']}")
    
    return success_count

if __name__ == "__main__":
    # Generate and save sample messages
    num_messages = 5  # Default
    
    # Check for command-line argument
    import sys
    if len(sys.argv) > 1:
        try:
            num_messages = int(sys.argv[1])
        except ValueError:
            pass
    
    save_sample_messages(num_messages)
    print(f"Generated {num_messages} sample messages. Check discord_message_history.json")