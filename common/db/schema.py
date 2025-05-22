"""
Database Schema Management Module

This module provides utilities for managing the database schema,
including creation, updates, and migrations.
"""
import logging
import os
import sys
from sqlalchemy import text

# Configure logging
logger = logging.getLogger(__name__)

# Get the app and db objects
from app import app, db
from common.db_models import *

def recreate_schema():
    """
    Drop and recreate all database tables.
    
    This is a destructive operation that will delete all data.
    Use with caution in production environments.
    
    Returns:
        bool: True if successful, False otherwise
    """
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
            return True
        except Exception as e:
            logger.error(f"Error recreating schema: {str(e)}")
            db.session.rollback()
            return False

def update_schema():
    """
    Update the database schema to match our models.
    
    This performs a non-destructive update to the database schema,
    adding new tables and columns but preserving existing data.
    
    Returns:
        bool: True if successful, False otherwise
    """
    with app.app_context():
        try:
            connection = db.engine.connect()
            
            # Check for specific tables and columns that might need updates
            # Example: Add 'text' column to ticker_setups table if it doesn't exist
            text_result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'ticker_setups' AND column_name = 'text'"))
            text_column_exists = text_result.fetchone() is not None

            if not text_column_exists:
                logger.info("Adding 'text' column to ticker_setups table...")
                connection.execute(text(
                    "ALTER TABLE ticker_setups ADD COLUMN text TEXT"))
                connection.commit()
                logger.info("'text' column added successfully!")
            else:
                logger.info("'text' column already exists in ticker_setups table.")
                
            # Check if message_id column exists in ticker_setups table
            message_id_result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'ticker_setups' AND column_name = 'message_id'"))
            message_id_column_exists = message_id_result.fetchone() is not None

            if not message_id_column_exists:
                logger.info("Adding 'message_id' column to ticker_setups table...")
                connection.execute(text(
                    "ALTER TABLE ticker_setups ADD COLUMN message_id INTEGER REFERENCES setup_messages(id)"))
                connection.commit()
                logger.info("'message_id' column added successfully!")
            else:
                logger.info("'message_id' column already exists in ticker_setups table.")
            
            # Use SQLAlchemy's create_all to add any missing tables
            # This won't modify existing tables
            db.create_all()
            logger.info("Schema update completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating schema: {e}")
            db.session.rollback()
            return False

def check_schema():
    """
    Check the database schema for consistency with our models.
    
    Returns:
        bool: True if schema is consistent, False otherwise
    """
    with app.app_context():
        try:
            # Check if required tables exist
            connection = db.engine.connect()
            tables = db.inspect(db.engine).get_table_names()
            
            required_tables = [
                'setup_messages',
                'ticker_setups',
                'signals',
                'biases',
                'bias_flips',
                'discord_messages',
                'events'
            ]
            
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.warning(f"Missing tables: {', '.join(missing_tables)}")
                return False
                
            logger.info("Database schema check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking schema: {e}")
            return False

if __name__ == "__main__":
    # Handle command-line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Schema Management Tool")
    parser.add_argument('action', choices=['recreate', 'update', 'check'], 
                        help='Action to perform: recreate (drop and recreate all tables), update (update schema), or check (check schema)')
    
    args = parser.parse_args()
    
    if args.action == 'recreate':
        if recreate_schema():
            print("Schema recreation successful")
            sys.exit(0)
        else:
            print("Schema recreation failed")
            sys.exit(1)
    elif args.action == 'update':
        if update_schema():
            print("Schema update successful")
            sys.exit(0)
        else:
            print("Schema update failed")
            sys.exit(1)
    elif args.action == 'check':
        if check_schema():
            print("Schema check passed")
            sys.exit(0)
        else:
            print("Schema check failed")
            sys.exit(1)