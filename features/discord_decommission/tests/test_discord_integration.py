"""
Discord Integration Test Tool

This module contains tests for Discord integration features.
"""
import os
import sys
import logging
import time
import unittest
from datetime import datetime
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestDiscordIntegration(unittest.TestCase):
    """Test Discord integration functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a minimal Flask application context
        self.app = Flask(__name__)
        self.app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        
        # Import after Flask app creation
        from app import db
        db.init_app(self.app)
        
        # Create the app context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Import Discord initialization
        from features.discord import initialize_discord
        
        # Initialize Discord
        self.discord_initialized = initialize_discord()
        if not self.discord_initialized:
            logger.warning("Discord integration not initialized")
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()
    
    def test_setup_handler(self):
        """Test the setup message handler directly."""
        if not self.discord_initialized:
            self.skipTest("Discord integration not initialized")
            
        # Create a test message with today's date
        today = datetime.now().strftime("%a, %b %d")
        test_message = f"""A+ Trade Setups ({today})

1. SPY: Rejection Near 500.5
   - Resistance: 500.5
   - Upper target: 495
   - Lower target: 490
   - Bearish bias below 500.5

2. AAPL: Breakout Above 180
   - Support: 180
   - Target 1: 185
   - Target 2: 190
   - Bullish bias above 180, bearish below 175"""

        logger.info("Testing setup handler with message for today's market")

        # Import the handler function
        from features.discord.setup_handler import handle_discord_setup_message

        # Process the message
        result = handle_discord_setup_message(test_message, datetime.now())

        self.assertIsNotNone(result, "Failed to process setup message")
        self.assertTrue(hasattr(result, 'id'), "Result should have an ID")
        
        # Log details about the extracted data
        ticker_symbols = [ts.symbol for ts in result.ticker_setups]
        logger.info(f"Extracted tickers: {ticker_symbols}")
        
        # Verify that we extracted the expected tickers
        self.assertIn("SPY", ticker_symbols, "SPY should be in extracted tickers")
        self.assertIn("AAPL", ticker_symbols, "AAPL should be in extracted tickers")
        
        # Verify signals and biases
        signal_count = sum(len(ts.signals) for ts in result.ticker_setups if hasattr(ts, 'signals'))
        logger.info(f"Extracted signals: {signal_count}")
        self.assertGreater(signal_count, 0, "Should have extracted at least one signal")
        
        bias_count = sum(1 for ts in result.ticker_setups if hasattr(ts, 'bias') and ts.bias is not None)
        logger.info(f"Extracted biases: {bias_count}")
        self.assertGreater(bias_count, 0, "Should have extracted at least one bias")

    def test_send_status(self):
        """Test sending a status message."""
        if not self.discord_initialized:
            self.skipTest("Discord integration not initialized")
            
        from features.discord.client import send_status_update

        logger.info("Testing status update")
        result = send_status_update("🔧 **Test Message**: Testing Discord integration")

        logger.info(f"Status update result: {result}")
        self.assertTrue(result, "Status update should succeed")


if __name__ == '__main__':
    unittest.main()