"""
Discord Events Test

Tests for Discord event publishing and handling.
"""
import unittest
import logging
from datetime import datetime
from flask import Flask
from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import DiscordMessageModel

logger = logging.getLogger(__name__)

class TestDiscordEvents(unittest.TestCase):
    """Test Discord event functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a minimal Flask application context
        self.app = Flask(__name__)
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        db.init_app(self.app)
        
        # Create the app context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create all tables
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_discord_message_event(self):
        """Test publishing a Discord message event."""
        message_data = {
            "message_id": "123456789",
            "content": "A+ Trade Setups (Thu, May 22)\n\n1. SPY: Rejection Near 500.5",
            "timestamp": datetime.utcnow().isoformat(),
            "channel_id": "test_channel",
            "author_id": "test_author"
        }

        # Publish the event
        success = publish_event(EventChannels.DISCORD_SETUP_MESSAGE, message_data)
        self.assertTrue(success, "Failed to publish Discord message event")
        
        # Verify the message was stored in the database
        message = DiscordMessageModel.query.filter_by(message_id="123456789").first()
        self.assertIsNotNone(message, "Message should be stored in the database")
        self.assertEqual(message.content, message_data["content"])
        
    def test_message_processing(self):
        """Test processing of Discord messages for trading setups."""
        # Create a test message
        today = datetime.now().strftime("%a, %b %d")
        message_content = f"""A+ Trade Setups ({today})

1. SPY: Rejection Near 500.5
   - Resistance: 500.5
   - Upper target: 495
   - Lower target: 490
   - Bearish bias below 500.5"""
        
        message_data = {
            "message_id": "987654321",
            "content": message_content,
            "timestamp": datetime.utcnow().isoformat(),
            "channel_id": "setup_channel",
            "author_id": "setup_author"
        }
        
        # Publish the message event
        success = publish_event(EventChannels.DISCORD_SETUP_MESSAGE, message_data)
        self.assertTrue(success, "Failed to publish setup message event")
        
        # Retrieve from database and check content
        message = DiscordMessageModel.query.filter_by(message_id="987654321").first()
        self.assertIsNotNone(message, "Setup message should be stored in the database")
        
        # Check for essential trading setup content
        self.assertIn("SPY", message.content, "Message should contain SPY ticker")
        self.assertIn("Rejection", message.content, "Message should contain signal type")
        self.assertIn("Bearish", message.content, "Message should contain bias")
        
        # If setup processing is implemented, additional verification would go here


if __name__ == '__main__':
    unittest.main()