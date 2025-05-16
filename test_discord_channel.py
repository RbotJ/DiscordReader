"""
Discord Channel Test Script

This script tests the Discord integration by sending test messages to Discord channels.
"""
import os
import sys
import argparse
import logging
from flask import Flask

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_discord_configuration():
    """Check Discord configuration."""
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment")
        return False
        
    bot_channel = os.environ.get('DISCORD_CHANNEL_BOT_DIALOGUE')
    setups_channel = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
    test_channel = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
    
    if not bot_channel:
        logger.warning("DISCORD_CHANNEL_BOT_DIALOGUE not found in environment")
    if not setups_channel:
        logger.warning("DISCORD_CHANNEL_APLUS_SETUPS not found in environment")
    if not test_channel:
        logger.warning("DISCORD_CHANNEL_TEST_HERE_ONE not found in environment")
        
    try:
        # Convert to integers to validate format
        if bot_channel:
            int(bot_channel)
        if setups_channel:
            int(setups_channel)
        if test_channel:
            int(test_channel)
    except ValueError:
        logger.error("One or more channel IDs are not valid integers")
        return False
        
    return bool(token and (bot_channel or setups_channel or test_channel))

def test_send_message(message, channel_target):
    """
    Test sending a message to a Discord channel.
    
    Args:
        message: The message to send
        channel_target: Target channel ('bot', 'test', or 'both')
        
    Returns:
        bool: Success status
    """
    # Create a minimal Flask application context
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    
    # Import after Flask app creation
    with app.app_context():
        # Import Discord client functions
        from features.discord.client import (
            send_bot_message, send_test_message, send_status_update, is_discord_available
        )
        
        if not is_discord_available:
            logger.error("Discord integration unavailable - missing configuration")
            return False
        
        # Test sending to appropriate channel(s)
        success = True
        
        if channel_target in ('bot', 'both'):
            logger.info("Sending test message to bot channel")
            result = send_bot_message(message)
            if not result:
                logger.error("Failed to send message to bot channel")
                success = False
        
        if channel_target in ('test', 'both'):
            logger.info("Sending test message to test channel")
            result = send_test_message(message)
            if not result:
                logger.error("Failed to send message to test channel")
                success = False
                
        if channel_target == 'status':
            logger.info("Sending status update")
            result = send_status_update(message)
            if not result:
                logger.error("Failed to send status update")
                success = False
                
        return success

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test Discord channel integration')
    parser.add_argument('--message', '-m', default='Test message from trading bot',
                        help='Message to send to Discord')
    parser.add_argument('--channel', '-c', choices=['bot', 'test', 'both', 'status'],
                        default='test', help='Target channel for message')
    args = parser.parse_args()
    
    # Check Discord configuration
    logger.info("Checking Discord configuration...")
    if not check_discord_configuration():
        logger.error("Discord configuration incomplete or invalid")
        return 1
    
    # Send test message
    logger.info(f"Sending test message: '{args.message}' to {args.channel} channel(s)")
    success = test_send_message(args.message, args.channel)
    
    if success:
        logger.info("Test message(s) sent successfully")
        return 0
    else:
        logger.error("Failed to send one or more test messages")
        return 1

if __name__ == '__main__':
    sys.exit(main())