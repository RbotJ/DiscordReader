"""
Discord Integration Test Tool

This script tests the Discord integration features.
"""
import os
import sys
import logging
import time
import argparse
from datetime import datetime
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_setup_handler():
    """Test the setup message handler directly."""
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
    
    if result:
        logger.info(f"Successfully processed setup message. ID: {result.id}")
        
        # Log details about the extracted data
        ticker_symbols = [ts.symbol for ts in result.ticker_setups]
        logger.info(f"Extracted tickers: {ticker_symbols}")
        
        signal_count = sum(len(ts.signals) for ts in result.ticker_setups if hasattr(ts, 'signals'))
        logger.info(f"Extracted signals: {signal_count}")
        
        bias_count = sum(1 for ts in result.ticker_setups if hasattr(ts, 'bias') and ts.bias is not None)
        logger.info(f"Extracted biases: {bias_count}")
        
        return True
    else:
        logger.error("Failed to process setup message")
        return False

def test_send_status():
    """Test sending a status message."""
    from features.discord.client import send_status_update
    
    logger.info("Testing status update")
    result = send_status_update("🔧 **Test Message**: Testing Discord integration")
    
    logger.info(f"Status update result: {result}")
    return result

def main():
    """Main function to test Discord integration."""
    parser = argparse.ArgumentParser(description='Test Discord integration features')
    parser.add_argument('--action', choices=['status', 'setup'], default='setup',
                        help='Action to test: status message or process setup')
    args = parser.parse_args()
    
    logger.info(f"Testing Discord integration: {args.action}")
    
    # Create a minimal Flask application context
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    
    # Import after Flask app creation
    from app import db
    db.init_app(app)
    
    with app.app_context():
        # Import Discord initialization
        from features.discord import initialize_discord
        
        # Initialize Discord
        success = initialize_discord()
        if not success:
            logger.error("Failed to initialize Discord integration")
            return 1
        
        # Test the requested action
        if args.action == 'status':
            result = test_send_status()
        elif args.action == 'setup':
            result = test_setup_handler()
        else:
            logger.error(f"Unknown action: {args.action}")
            return 1
        
        logger.info(f"Test {'succeeded' if result else 'failed'}")
        return 0 if result else 1

if __name__ == '__main__':
    sys.exit(main())