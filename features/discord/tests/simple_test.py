"""
Simple Discord Test

A simplified script to test the Discord integration in mock mode.
"""
import os
import logging
from flask import Flask
from common.db import db

# Set up logging
logger = logging.getLogger(__name__)

def is_discord_available():
    """
    Check if Discord integration is available.
    
    Returns:
        True if Discord is available, False otherwise
    """
    # Check for Discord token and channel IDs
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    test_channel = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
    
    if not bot_token:
        logger.error("Discord bot token not found")
        return False
    
    if not test_channel:
        logger.error("Test channel ID not found")
        return False
    
    return True

def test_discord_connection():
    """
    Test the Discord connection.
    
    Returns:
        True if successful, False otherwise
    """
    # Check if Discord is available
    if not is_discord_available():
        return False
    
    # Import functionality to send test message
    try:
        # This would be implemented in a Discord client module
        from features.discord.client import send_test_message
        
        # Test sending message to test channel
        message = "This is a test message from the A+ Trading App"
        logger.info(f"Sending test message: {message}")
        
        result = send_test_message(message)
        
        if result:
            logger.info("Test message sent successfully")
            return True
        else:
            logger.error("Failed to send test message")
            return False
    except ImportError as e:
        logger.error(f"Failed to import Discord client: {e}")
        return False

# Command-line entry point
def main():
    """Command-line entry point for testing Discord integration."""
    # Configure logging for command-line use
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create a Flask app context for database access
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    db.init_app(app)
    
    with app.app_context():
        if test_discord_connection():
            logger.info("Discord integration test successful")
            return 0
        else:
            logger.error("Discord integration test failed")
            return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())