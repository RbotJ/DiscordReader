"""
Discord Messaging Tests

Tests for basic Discord messaging functionality.
"""
import os
import unittest
import logging
from flask import Flask
from app import db

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestDiscordMessaging(unittest.TestCase):
    """Test Discord messaging functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Check for Discord token and channel IDs
        self.bot_token = os.environ.get('DISCORD_BOT_TOKEN')
        self.test_channel = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
        
        # Create a Flask app context for database access
        self.app = Flask(__name__)
        self.app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        db.init_app(self.app)
        
        # Create the app context
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()
    
    def test_send_message(self):
        """Test sending a simple message to Discord."""
        if not self.bot_token or not self.test_channel:
            self.skipTest("Discord credentials not available")
        
        # Import after app context creation
        from features.discord.client import is_discord_available, send_test_message
        
        if not is_discord_available:
            self.skipTest("Discord integration unavailable")
        
        # Test sending message to test channel
        message = "This is a test message from the A+ Trading App"
        logger.info(f"Sending test message: {message}")
        
        result = send_test_message(message)
        self.assertTrue(result, "Message should be sent successfully")


if __name__ == '__main__':
    unittest.main()