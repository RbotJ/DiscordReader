"""
Database Schema Validator

Prevents database query errors by validating schema before execution.
"""
import logging
from sqlalchemy import inspect
from common.db import db

logger = logging.getLogger(__name__)

def validate_table_exists(table_name: str) -> bool:
    """Validate that a table exists in the database."""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        return table_name in tables
    except Exception as e:
        logger.error(f"Error checking table existence: {e}")
        return False

def validate_column_exists(table_name: str, column_name: str) -> bool:
    """Validate that a column exists in the specified table."""
    try:
        inspector = inspect(db.engine)
        columns = inspector.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        return column_name in column_names
    except Exception as e:
        logger.error(f"Error checking column existence: {e}")
        return False

def validate_schema_compatibility(model_class, required_columns: list) -> dict:
    """
    Validate that a model's table has all required columns.
    
    Returns:
        dict: {'valid': bool, 'missing_columns': list, 'table_name': str}
    """
    table_name = model_class.__tablename__
    
    if not validate_table_exists(table_name):
        return {
            'valid': False,
            'missing_columns': required_columns,
            'table_name': table_name,
            'error': 'Table does not exist'
        }
    
    missing_columns = []
    for column in required_columns:
        if not validate_column_exists(table_name, column):
            missing_columns.append(column)
    
    return {
        'valid': len(missing_columns) == 0,
        'missing_columns': missing_columns,
        'table_name': table_name
    }

def log_schema_mismatch(validation_result: dict):
    """Log schema validation failures with helpful information."""
    if not validation_result['valid']:
        logger.error(
            f"Schema validation failed for table '{validation_result['table_name']}'. "
            f"Missing columns: {validation_result['missing_columns']}. "
            f"Please check your database schema or update your queries."
        )