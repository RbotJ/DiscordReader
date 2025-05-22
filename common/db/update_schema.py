"""
Update Database Schema

This script updates the database schema to match our models.
"""
import os
import sys
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import our Flask app and database
from main import app, db
from common.db_models import *

def update_schema():
    """Update the database schema to match our models."""
    with app.app_context():
        connection = db.engine.connect()
        try:
            # Check if text column exists in ticker_setups table
            text_result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'ticker_setups' AND column_name = 'text'"))
            text_column_exists = text_result.fetchone() is not None

            # Check if message_id column exists in ticker_setups table
            message_id_result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'ticker_setups' AND column_name = 'message_id'"))
            message_id_column_exists = message_id_result.fetchone() is not None

            # Add text column if it doesn't exist
            if not text_column_exists:
                logger.info("Adding 'text' column to ticker_setups table...")
                connection.execute(text(
                    "ALTER TABLE ticker_setups ADD COLUMN text TEXT"))
                connection.commit()
                logger.info("'text' column added successfully!")
            else:
                logger.info("'text' column already exists in ticker_setups table.")

            # Add message_id column if it doesn't exist
            if not message_id_column_exists:
                logger.info("Adding 'message_id' column to ticker_setups table...")
                connection.execute(text(
                    "ALTER TABLE ticker_setups ADD COLUMN message_id INTEGER NOT NULL DEFAULT 0"))
                connection.execute(text(
                    "ALTER TABLE ticker_setups ADD CONSTRAINT fk_ticker_setups_message_id FOREIGN KEY (message_id) REFERENCES setup_messages (id) ON DELETE CASCADE"))
                connection.commit()
                logger.info("'message_id' column and foreign key constraint added successfully!")
            else:
                logger.info("'message_id' column already exists in ticker_setups table.")

            logger.info("Schema update completed successfully!")

        except Exception as e:
            connection.rollback()
            logger.error(f"Error updating schema: {str(e)}")
            raise
        finally:
            connection.close()

if __name__ == "__main__":
    update_schema()