"""
Simple Discord Test

A simplified script to test the Discord integration in mock mode.
"""
import os
import logging
from flask import Flask
from app import db

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test Discord integration in mock mode."""
    # Check for Discord token and channel IDs
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    test_channel = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
    
    if not bot_token:
        logger.error("Discord bot token not found")
        return
    
    if not test_channel:
        logger.error("Test channel ID not found")
        return
    
    logger.info(f"Using Discord test channel ID: {test_channel}")
    
    # Create a Flask app context for database access
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    db.init_app(app)
    
    with app.app_context():
        # Import after app context creation
        from features.discord.client import is_discord_available, send_test_message
        
        if not is_discord_available:
            logger.error("Discord integration unavailable")
            return
        
        # Test sending message to test channel
        message = "This is a test message from the A+ Trading App"
        logger.info(f"Sending test message: {message}")
        
        result = send_test_message(message)
        
        if result:
            logger.info("Test message sent successfully")
        else:
            logger.error("Failed to send test message")

if __name__ == '__main__':
    main()