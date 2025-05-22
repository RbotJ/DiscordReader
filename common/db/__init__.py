"""
Database Package

This package provides database access and utilities for the trading application.
"""
import os
import logging
from flask_sqlalchemy import SQLAlchemy

# Create a logger for this module
logger = logging.getLogger(__name__)

# Initialize the database
db = SQLAlchemy()

def initialize_db(app):
    """Initialize the database with the Flask app."""
    try:
        # Configure database
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        
        # Initialize with the app
        db.init_app(app)
        
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False