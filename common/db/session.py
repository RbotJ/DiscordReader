"""
Database Session Management

Handles Flask-SQLAlchemy database instance, initialization, and session management.
"""

from flask_sqlalchemy import SQLAlchemy
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create a SQLAlchemy instance
db = SQLAlchemy()

def initialize_db(app):
    """
    Initialize database with app context.
    
    Args:
        app: Flask application instance
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        db.init_app(app)
        with app.app_context():
            db.create_all()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def get_session():
    """
    Get the current database session.
    
    Returns:
        SQLAlchemy session
    """
    return db.session

def commit_session():
    """
    Commit the current database session.
    
    Returns:
        bool: True if commit successful, False otherwise
    """
    try:
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to commit session: {e}")
        db.session.rollback()
        return False

def rollback_session():
    """
    Rollback the current database session.
    """
    try:
        db.session.rollback()
        logger.debug("Database session rolled back")
    except Exception as e:
        logger.error(f"Failed to rollback session: {e}")

def close_session():
    """
    Close the current database session.
    """
    try:
        db.session.close()
        logger.debug("Database session closed")
    except Exception as e:
        logger.error(f"Failed to close session: {e}")