"""
Integration tests for the setup API endpoints.
"""
import unittest
import json
import os
from datetime import date

# Set test environment variable
os.environ["TESTING"] = "True"

# Import app after setting test environment
# Mock Redis-related functions to prevent attempts to connect
import sys
import unittest.mock

# Replace Redis dependencies with mock objects
sys.modules['redis'] = unittest.mock.MagicMock()
sys.modules['redis.exceptions'] = unittest.mock.MagicMock()

# Now import app components
from app import app, db
from features.setups.api import create_setup_from_message
from features.setups.parser import parse_setup_message
from common.db_models import SetupModel, TickerSetupModel, SignalModel, BiasModel

# Patch redis_client
import common.redis_utils
common.redis_utils.redis_client = unittest.mock.MagicMock()
common.redis_utils.is_redis_available = lambda: False
from tests.fixtures.sample_messages import (
    SIMPLE_MESSAGE,
    MULTI_TICKER_MESSAGE,
    ALTERNATE_FORMAT_MESSAGE,
    COMPLEX_BIAS_MESSAGE
)


class TestSetupAPI(unittest.TestCase):
    """Test the setup API endpoints."""
    
    def setUp(self):
        """Set up test client and database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        # Create all tables
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_parse_endpoint(self):
        """Test the parse endpoint."""
        with app.app_context():
            response = self.client.post('/api/setups/parse', 
                               json={'text': SIMPLE_MESSAGE, 'source': 'test'})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertEqual(data['status'], 'success')
            self.assertIn('data', data)
            self.assertEqual(len(data['data']['setups']), 1)
            self.assertEqual(data['data']['setups'][0]['symbol'], 'SPY')
    
    def test_webhook_endpoint(self):
        """Test the webhook endpoint."""
        with app.app_context():
            response = self.client.post('/api/setups/webhook', 
                               json={'text': SIMPLE_MESSAGE, 'source': 'test'})
            
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            
            self.assertEqual(data['status'], 'success')
            self.assertIn('setup_id', data)
            
            # Check that the setup was actually created in the database
            setup = SetupModel.query.get(data['setup_id'])
            self.assertIsNotNone(setup)
            self.assertEqual(len(setup.ticker_setups), 1)
            self.assertEqual(setup.ticker_setups[0].symbol, 'SPY')
    
    def test_get_setups_endpoint(self):
        """Test the get setups endpoint."""
        with app.app_context():
            # First create some setups
            setup_message = parse_setup_message(SIMPLE_MESSAGE, 'test')
            setup1 = create_setup_from_message(setup_message)
            db.session.commit()
            
            setup_message = parse_setup_message(MULTI_TICKER_MESSAGE, 'test')
            setup2 = create_setup_from_message(setup_message)
            db.session.commit()
            
            # Now test the endpoint
            response = self.client.get('/api/setups')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertEqual(data['status'], 'success')
            self.assertEqual(len(data['data']), 2)
    
    def test_get_setup_endpoint(self):
        """Test the get setup endpoint."""
        with app.app_context():
            # First create a setup
            setup_message = parse_setup_message(MULTI_TICKER_MESSAGE, 'test')
            setup = create_setup_from_message(setup_message)
            db.session.commit()
            
            # Now test the endpoint
            response = self.client.get(f'/api/setups/{setup.id}')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['data']['id'], setup.id)
            self.assertEqual(len(data['data']['tickers']), 3)
    
    def test_get_nonexistent_setup(self):
        """Test getting a setup that doesn't exist."""
        with app.app_context():
            response = self.client.get('/api/setups/9999')
            
            self.assertEqual(response.status_code, 404)
            data = json.loads(response.data)
            
            self.assertEqual(data['status'], 'error')
            self.assertIn('message', data)
    
    def test_webhook_invalid_input(self):
        """Test the webhook endpoint with invalid input."""
        with app.app_context():
            # No text field
            response = self.client.post('/api/setups/webhook', 
                               json={'source': 'test'})
            
            self.assertEqual(response.status_code, 400)
            
            # Not JSON
            response = self.client.post('/api/setups/webhook', 
                               data='not json')
            
            self.assertEqual(response.status_code, 400)
    
    def test_create_complex_setup(self):
        """Test creating a complex setup."""
        with app.app_context():
            setup_message = parse_setup_message(COMPLEX_BIAS_MESSAGE, 'test')
            setup = create_setup_from_message(setup_message)
            db.session.commit()
            
            # Check the database
            ticker_setup = setup.ticker_setups[0]
            self.assertEqual(ticker_setup.symbol, 'SPY')
            
            # Check bias
            bias = ticker_setup.bias
            self.assertIsNotNone(bias)
            self.assertEqual(bias.direction, 'bearish')
            self.assertEqual(bias.condition, 'below')
            self.assertEqual(bias.price, 562.25)
            self.assertEqual(bias.flip_direction, 'bullish')
            self.assertEqual(bias.flip_price_level, 564.1)
            
            # Check signals
            signals = ticker_setup.signals
            self.assertGreater(len(signals), 0)
            
            # Find specific signal types
            breakdown_signals = [s for s in signals if s.category == 'breakdown']
            breakout_signals = [s for s in signals if s.category == 'breakout']
            rejection_signals = [s for s in signals if s.category == 'rejection']
            
            self.assertGreater(len(breakdown_signals), 0)
            self.assertGreater(len(breakout_signals), 0)
            self.assertGreater(len(rejection_signals), 0)


if __name__ == '__main__':
    unittest.main()