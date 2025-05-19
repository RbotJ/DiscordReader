"""
Database Utilities

A module providing a shared SQLAlchemy database instance and common database operations.
"""

import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Setup logging
logger = logging.getLogger(__name__)

# Create a base class for declarative model definitions
class Base(DeclarativeBase):
    pass

# Create a SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """
    Initialize the database with the Flask application.
    
    Args:
        app: Flask application instance
        
    Returns:
        bool: True if database was initialized successfully, False otherwise
    """
    try:
        # Configure database URI
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        
        # Initialize the database
        db.init_app(app)
        
        # Create all tables if they don't exist
        with app.app_context():
            db.create_all()
            logger.info("Database initialized successfully")
            
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def execute_query(query, params=None, fetch_one=False):
    """
    Execute a raw SQL query safely.
    
    Args:
        query (str): SQL query to execute
        params (dict, optional): Parameters for the query
        fetch_one (bool, optional): If True, fetch one result, otherwise fetch all
        
    Returns:
        list or dict: Query results or None if an error occurred
    """
    try:
        from sqlalchemy import text
        
        # Create SQLAlchemy text object
        sql_text = text(query)
        
        # Execute the query
        result = db.session.execute(sql_text, params or {})
        
        # Fetch results
        if fetch_one:
            return result.fetchone()
        else:
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        db.session.rollback()
        return None

def check_database_connection():
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        # Simple query to test connection
        result = execute_query("SELECT 1", fetch_one=True)
        return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False