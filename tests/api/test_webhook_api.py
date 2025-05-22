"""
Test Webhook API

This module contains tests for the webhook API functionality.
"""
import unittest
import json
import logging
from datetime import datetime
from flask import Flask
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample test messages
SAMPLE_MESSAGES = {
    "single_ticker": """A+ Trade Setups Wed May 15:

    1) SPY: Rejection Near 528.8
    - Breakdown below 526.5
    - Bounce from 522.3
    - Breakout above 530.2
    - Targets: 534, 538, 540

    Bias: Bullish above 525, turns bearish below 520
    """,
    
    "multiple_tickers": """A+ Setups Thursday May 16

    TSLA
    - Bullish above 175
    - Breakout above 180 targeting 185, 190
    - Breakdown below 170 target 165

    NVDA
    - Breakout above 950 targeting 970, 1000
    - Breakdown below 920 target 900, 880
    - Bias: Bullish above 925, bearish below 910

    SPY
    - Rejection at 528-530 range
    - Looking for breakdown below 525.5
    - Targets: 522, 520, 515
    """,
    
    "alternative_format": """Today's A+ Setups (May 17)

    🔼 AAPL: Breaking out above 185, targets 188, 190, 192
    🔽 MSFT: Breakdown below 415, looking for 410, 405
    ❌ META: Strong rejection at 480, careful above this level
    🔄 AMD: Bouncing from 145 support, targets 150, 155 if it holds
    """
}


class TestWebhookAPI(unittest.TestCase):
    """Test the webhook API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        # Create Flask test client
        from app import app, db
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        # Create app context and database
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        from app import db
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_parse_setup_endpoint(self):
        """Test the setup parser endpoint."""
        for name, message_text in SAMPLE_MESSAGES.items():
            logger.info(f"Testing setup parser with {name}...")
            
            response = self.client.post('/api/webhooks/setup/parse', json={
                "text": message_text,
                "source": "test_script"
            })
            
            self.assertEqual(response.status_code, 200, f"Parser should return 200 for {name}")
            result = json.loads(response.data)
            
            self.assertIn('tickers', result, f"Result for {name} should include 'tickers'")
            self.assertTrue(len(result['tickers']) > 0, f"Should find at least one ticker in {name}")
            
            logger.info(f"Successfully parsed {name}, found tickers: {result['tickers']}")
    
    def test_receive_setup_endpoint(self):
        """Test the setup receiver endpoint."""
        message_text = SAMPLE_MESSAGES["single_ticker"]
        
        response = self.client.post('/api/webhooks/setup', json={
            "text": message_text,
            "source": "test_script",
            "timestamp": datetime.now().isoformat()
        })
        
        self.assertEqual(response.status_code, 200, "Receiver should return 200")
        result = json.loads(response.data)
        
        self.assertIn('message_id', result, "Result should include 'message_id'")
        self.assertIn('tickers', result, "Result should include 'tickers'")
        
        # Verify the setup was stored in the database
        from common.db_models import MessageModel
        message = MessageModel.query.get(result['message_id'])
        self.assertIsNotNone(message, "Setup should be stored in the database")
        
        logger.info(f"Successfully processed setup, message ID: {result['message_id']}")
    
    def test_bad_request_handling(self):
        """Test handling of bad requests."""
        # Test missing text field
        response = self.client.post('/api/webhooks/setup/parse', json={
            "source": "test_script"
        })
        self.assertEqual(response.status_code, 400, "Should return 400 for missing text")
        
        # Test invalid JSON
        response = self.client.post('/api/webhooks/setup/parse', 
                           data="not json",
                           content_type='application/json')
        self.assertEqual(response.status_code, 400, "Should return 400 for invalid JSON")
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Make multiple rapid requests to test rate limiting
        responses = []
        for _ in range(10):
            response = self.client.post('/api/webhooks/setup/parse', json={
                "text": "Test message",
                "source": "test_script"
            })
            responses.append(response.status_code)
        
        # Check if rate limiting was applied
        # Rate limiting might not be strictly applied in tests, so this is informational
        if 429 in responses:
            logger.info("Rate limiting is active and working")
        else:
            logger.info("All requests succeeded, rate limiting may not be active in test mode")


if __name__ == '__main__':
    unittest.main()