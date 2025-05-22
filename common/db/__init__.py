"""
Database Module

This module provides access to the database for the trading application.
"""
import os
import logging
import contextlib
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Session

# Initialize logger
logger = logging.getLogger(__name__)

# Define SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with our base class
db = SQLAlchemy(model_class=Base)

def initialize_db(app=None):
    """
    Initialize the database connection.
    
    Args:
        app: Flask application instance
    
    Returns:
        True if successful, False otherwise
    """
    if app is None:
        logger.warning("No Flask app provided to initialize_db")
        return False
        
    try:
        # Configure database
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            app.config["SQLALCHEMY_DATABASE_URI"] = database_url
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_recycle": 300,
                "pool_pre_ping": True,
            }
        else:
            logger.warning("DATABASE_URL not set. Using SQLite for development.")
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///aplus_trading.db"
            
        # Initialize SQLAlchemy with the app
        db.init_app(app)
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

@contextlib.contextmanager
def db_session():
    """
    Context manager for database sessions.
    
    Yields:
        Session: SQLAlchemy session instance
        
    Example:
        with db_session() as session:
            results = session.query(MyModel).all()
    """
    session = db.session
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

# Export the db object for use in other modules
__all__ = ['db', 'initialize_db', 'Base', 'db_session']