"""
Test Webhook API

This script tests the webhook API by sending a variety of setup messages
and verifying that they are properly processed and stored in the database.
"""
import json
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Server URL - using localhost for testing
BASE_URL = "http://localhost:5000"

from common.db import db
from common.db_models import EventModel

def clear_test_data():
    db.session.query(EventModel).delete()
    db.session.commit()

def test_parse_setup(message_text):
    """
    Test the setup parser endpoint.

    Args:
        message_text: The message text to parse

    Returns:
        Response from the API
    """
    url = f"{BASE_URL}/api/webhooks/setup/parse"

    payload = {
        "text": message_text,
        "source": "test_script"
    }

    logger.info(f"Testing setup parser with message: {message_text[:50]}...")

    try:
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Parsed setup successfully: {len(result.get('tickers', []))} tickers found")
            return result
        else:
            logger.error(f"Failed to parse setup: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error during API request: {str(e)}")
        return None

def test_receive_setup(message_text):
    """
    Test the setup receiver endpoint.

    Args:
        message_text: The message text to process

    Returns:
        Response from the API
    """
    url = f"{BASE_URL}/api/webhooks/setup"

    payload = {
        "text": message_text,
        "source": "test_script",
        "timestamp": datetime.now().isoformat()
    }

    logger.info(f"Testing setup receiver with message: {message_text[:50]}...")

    try:
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Processed setup successfully: Message ID {result.get('message_id')} with {len(result.get('tickers', []))} tickers")
            return result
        else:
            logger.error(f"Failed to process setup: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error during API request: {str(e)}")
        return None

def run_tests():
    """Run all webhook API tests."""
    # Sample message 1: Single ticker with multiple signals
    sample1 = """A+ Trade Setups Wed May 15:

    1) SPY: Rejection Near 528.8
    - Breakdown below 526.5
    - Bounce from 522.3
    - Breakout above 530.2
    - Targets: 534, 538, 540

    Bias: Bullish above 525, turns bearish below 520
    """

    # Sample message 2: Multiple tickers
    sample2 = """A+ Setups Thursday May 16

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
    """

    # Sample message 3: Different format
    sample3 = """Today's A+ Setups (May 17)

    🔼 AAPL: Breaking out above 185, targets 188, 190, 192
    🔽 MSFT: Breakdown below 415, looking for 410, 405
    ❌ META: Strong rejection at 480, careful above this level
    🔄 AMD: Bouncing from 145 support, targets 150, 155 if it holds
    """

    # Test parser endpoint
    logger.info("Testing setup parser endpoint...")
    parse_result1 = test_parse_setup(sample1)
    parse_result2 = test_parse_setup(sample2)
    parse_result3 = test_parse_setup(sample3)

    if all([parse_result1, parse_result2, parse_result3]):
        logger.info("All parser tests completed successfully!")
    else:
        logger.warning("Some parser tests failed.")

    # Test receiver endpoint
    logger.info("Testing setup receiver endpoint...")
    receive_result1 = test_receive_setup(sample1)

    if receive_result1:
        logger.info("Setup receiver test completed successfully!")
    else:
        logger.warning("Setup receiver test failed.")

if __name__ == "__main__":
    run_tests()