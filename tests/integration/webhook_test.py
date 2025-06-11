"""
Integration Test for Webhook API

This script tests the webhook API by sending a variety of setup messages
and verifying that they are properly processed and notifications are sent.
"""
import sys
import json
import logging
import requests
from datetime import datetime, timezone
from common.utils import utc_now

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Webhook URL
WEBHOOK_URL = "http://localhost:5000/api/v1/webhooks/setup"

def send_setup_message(message_text, source="test_script"):
    """
    Send a setup message to the webhook API.
    
    Args:
        message_text: The setup message text
        source: Source of the message
        
    Returns:
        Response from the webhook API
    """
    # Build the request payload
    payload = {
        "text": message_text,
        "source": source,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Send the request
    logger.info(f"Sending setup message to webhook API: {message_text[:50]}...")
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Check the response
        if response.status_code == 201:
            logger.info(f"Setup message successfully processed: {response.json()}")
            return response.json()
        else:
            logger.error(f"Error sending setup message: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception sending setup message: {e}")
        return None

def test_simple_setup():
    """Test a simple setup message with a single ticker."""
    message = """A+ Trade Setups (Fri, May 17)

1. QQQ: Breakout Above 450
   - Support: 450
   - Target 1: 455
   - Target 2: 460
   - Bullish bias above 450, bearish below 445"""
    
    return send_setup_message(message, "simple_test")

def test_multi_ticker_setup():
    """Test a setup message with multiple tickers."""
    message = """A+ Trade Setups (Fri, May 17)

1. IWM: Breakdown Below 205
   - Resistance: 205
   - Target 1: 200
   - Target 2: 195
   - Bearish bias below 205, bullish above 210

2. GLD: Bounce at 225
   - Support: 225
   - Target: 230
   - Bullish bias above 225

3. AMZN: Rejection Near 190
   - Resistance: 190
   - Target 1: 185
   - Target 2: 180
   - Bearish bias below 190"""
    
    return send_setup_message(message, "multi_ticker_test")

def test_emoji_setup():
    """Test a setup message with emojis."""
    message = """A+ Trade Setups (Fri, May 17) 🚀

1. AMD: 🔼 Above 145
   - Support: 145
   - Target 1: 150 🎯
   - Target 2: 155 🎯
   - Bullish bias above 145 📈, bearish below 140 📉

2. COST: 🔽 Below 780
   - Resistance: 780 ❌
   - Target 1: 775 🎯
   - Target 2: 770 🎯
   - Bearish bias below 780"""
    
    return send_setup_message(message, "emoji_test")

def main():
    """Run integration tests for the webhook API."""
    logger.info("Starting webhook API integration tests")
    
    # Test simple setup
    logger.info("Testing simple setup message")
    simple_result = test_simple_setup()
    
    # Test multi-ticker setup
    logger.info("Testing multi-ticker setup message")
    multi_result = test_multi_ticker_setup()
    
    # Test emoji setup
    logger.info("Testing setup message with emojis")
    emoji_result = test_emoji_setup()
    
    # Print summary
    logger.info("=== Test Summary ===")
    logger.info(f"Simple setup test: {'SUCCESS' if simple_result else 'FAILURE'}")
    logger.info(f"Multi-ticker setup test: {'SUCCESS' if multi_result else 'FAILURE'}")
    logger.info(f"Emoji setup test: {'SUCCESS' if emoji_result else 'FAILURE'}")
    
    # Return success if all tests passed
    success = bool(simple_result and multi_result and emoji_result)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())