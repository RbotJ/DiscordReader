"""
Discord Integration Test Tool

This script tests the Discord integration features.
"""
import os
import sys
import logging
import time
import argparse
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to test Discord integration."""
    parser = argparse.ArgumentParser(description='Test Discord integration features')
    parser.add_argument('--action', choices=['status', 'alert', 'setup'], default='status',
                        help='Action to test: status message, trade alert, or process setup')
    args = parser.parse_args()
    
    logger.info(f"Testing Discord integration: {args.action}")
    
    # Create a minimal Flask application context
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    
    # Import after Flask app creation
    from app import db
    db.init_app(app)
    
    with app.app_context():
        # Import Discord test utils
        from features.discord import init_discord
        from features.discord.test_utils import (
            test_send_status_message, test_send_trade_alert,
            test_process_setup_message
        )
        
        # Initialize Discord
        success = init_discord()
        if not success:
            logger.error("Failed to initialize Discord integration")
            return 1
        
        # Wait for client to be ready
        logger.info("Waiting for Discord client to be ready...")
        time.sleep(5)
        
        # Test the requested action
        if args.action == 'status':
            result = test_send_status_message()
            logger.info(f"Status message test {'succeeded' if result else 'failed'}")
        elif args.action == 'alert':
            result = test_send_trade_alert()
            logger.info(f"Trade alert test {'succeeded' if result else 'failed'}")
        elif args.action == 'setup':
            result = test_process_setup_message()
            logger.info(f"Setup processing test {'succeeded' if result else 'failed'}")
        
        # Give time for async operations to complete
        logger.info("Waiting for operations to complete...")
        time.sleep(3)
        
        return 0 if result else 1

if __name__ == '__main__':
    sys.exit(main())