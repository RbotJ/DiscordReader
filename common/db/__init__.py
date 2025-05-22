"""
Database Module

This module provides access to the database for the trading application.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app import db

logger = logging.getLogger(__name__)

def init_db():
    """
    Initialize the database connection.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # The db is already initialized in app.py
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

# Export the db object for use in other modules
__all__ = ['db', 'init_db']