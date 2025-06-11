"""
Test Setup Message Handler

This script tests the setup message handler functionality.
"""
import os
import sys
import argparse
import logging
from datetime import datetime, timezone
from flask import Flask
from common.utils import utc_now

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Example A+ setup message for testing
EXAMPLE_SETUP_MESSAGE = """A+ Trade Setups (Wed, May 15)

1. SPY: Rejection Near 588.8
   - Resistance: 588.8 (gap fill)
   - Upper target: 584.2
   - Lower target: 578.6
   - Bearish bias above 588.8

2. NVDA: Breakout Above 925
   - Support: 925 (previous high)
   - Target 1: 945
   - Target 2: 960
   - Bullish bias above 925, bearish below 910

3. MSFT: Breakdown Below 412.5
   - Resistance: 412.5 (previous support)
   - Target 1: 405
   - Target 2: 398
   - Bearish bias below 412.5

4. AAPL: Bounce Near 182.5
   - Support: 182.5 (trend line)
   - Target: 188
   - Aggressive bullish bias above 182.5, flips bearish below 180
"""

from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import SetupMessageModel

def test_setup_handler():
    """Test the setup message handler functionality."""
    # Create a minimal Flask application context
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

    # Import after Flask app creation
    from app import db
    db.init_app(app)

    with app.app_context():
        # Import setup handler
        from features.discord.setup_handler import extract_setup_date, handle_discord_setup_message

        # Test date extraction
        message_date = datetime.now()
        extracted_date = extract_setup_date(EXAMPLE_SETUP_MESSAGE, message_date)
        logging.info(f"Extracted date: {extracted_date}")

        # Test message handling (this would create database entries)
        logging.info("Processing example setup message...")
        result = handle_discord_setup_message(EXAMPLE_SETUP_MESSAGE, message_date)

        if result:
            logging.info(f"Successfully processed setup message, ID: {result.id}")

            # Log tickers extracted
            ticker_symbols = [ts.symbol for ts in result.ticker_setups]
            logging.info(f"Extracted tickers: {ticker_symbols}")

            return True
        else:
            logging.error("Failed to process setup message")
            return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test setup message handler')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show verbose output')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        success = test_setup_handler()
        return 0 if success else 1
    except Exception as e:
        logging.exception(f"Error testing setup handler: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())