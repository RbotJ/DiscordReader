"""
Recreate Database Schema

This script drops all tables and recreates them from our models.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import our Flask app and database
from main import app, db

def recreate_schema():
    """Drop and recreate all database tables."""
    with app.app_context():
        try:
            # Drop all tables with CASCADE option using raw SQL
            logger.info("Dropping all tables with CASCADE option...")
            db.session.execute(db.text("""
                DO $$ 
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """))
            db.session.commit()
            logger.info("All tables dropped successfully.")
            
            # Create all tables from our models
            logger.info("Creating all tables from models...")
            db.create_all()
            logger.info("All tables created successfully!")
            
            logger.info("Database schema recreation completed successfully!")
        except Exception as e:
            logger.error(f"Error recreating schema: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    recreate_schema()