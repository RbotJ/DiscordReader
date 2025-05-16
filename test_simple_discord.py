"""
Simple Discord Test

A minimal test for Discord integration that uses our existing client.
"""
import os
import logging
import sys
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test sending a simple message to Discord."""
    # Create a minimal flask app context
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    
    from app import db
    db.init_app(app)
    
    with app.app_context():
        # Import our discord client
        from features.discord.client import send_test_message, send_status_update
        
        # Try to send a test message
        logger.info("Sending test message to Discord...")
        result = send_test_message("🔔 **Test Alert**: This is a test message from our trading application!")
        logger.info(f"Test message result: {result}")
        
        # Try to send a status update
        logger.info("Sending status update to Discord...")
        result = send_status_update("The trading application has been updated with new notification features!")
        logger.info(f"Status update result: {result}")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())