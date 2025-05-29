"""
Migration Helper Functions

Utility functions to assist with database migrations and schema management.
"""

import logging
from sqlalchemy import text
from .session import db

# Setup logging
logger = logging.getLogger(__name__)

def run_migration_script(script_path: str):
    """
    Execute a migration script file.
    
    Args:
        script_path (str): Path to the SQL migration script
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(script_path, 'r') as file:
            sql_content = file.read()
            
        # Split on semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for statement in statements:
            db.session.execute(text(statement))
            
        db.session.commit()
        logger.info(f"Migration script {script_path} executed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error executing migration script {script_path}: {e}")
        db.session.rollback()
        return False

def create_migration_table():
    """
    Create a migration tracking table if it doesn't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64)
        )
        """
        
        db.session.execute(text(create_table_sql))
        db.session.commit()
        logger.debug("Migration history table created/verified")
        return True
        
    except Exception as e:
        logger.error(f"Error creating migration history table: {e}")
        db.session.rollback()
        return False

def record_migration(migration_name: str, checksum: str = None):
    """
    Record a migration as completed.
    
    Args:
        migration_name (str): Name of the migration
        checksum (str, optional): Checksum of the migration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        insert_sql = """
        INSERT INTO migration_history (migration_name, checksum) 
        VALUES (:migration_name, :checksum)
        """
        
        db.session.execute(text(insert_sql), {
            'migration_name': migration_name,
            'checksum': checksum
        })
        db.session.commit()
        logger.info(f"Migration {migration_name} recorded")
        return True
        
    except Exception as e:
        logger.error(f"Error recording migration {migration_name}: {e}")
        db.session.rollback()
        return False

def is_migration_applied(migration_name: str):
    """
    Check if a migration has been applied.
    
    Args:
        migration_name (str): Name of the migration
        
    Returns:
        bool: True if migration has been applied, False otherwise
    """
    try:
        check_sql = """
        SELECT COUNT(*) as count FROM migration_history 
        WHERE migration_name = :migration_name
        """
        
        result = db.session.execute(text(check_sql), {
            'migration_name': migration_name
        }).fetchone()
        
        return result[0] > 0 if result else False
        
    except Exception as e:
        logger.error(f"Error checking migration {migration_name}: {e}")
        return False

def get_applied_migrations():
    """
    Get list of all applied migrations.
    
    Returns:
        list: List of applied migration names
    """
    try:
        query_sql = """
        SELECT migration_name, executed_at FROM migration_history 
        ORDER BY executed_at ASC
        """
        
        result = db.session.execute(text(query_sql)).fetchall()
        return [
            {
                'name': row[0], 
                'executed_at': row[1]
            } 
            for row in result
        ]
        
    except Exception as e:
        logger.error(f"Error getting applied migrations: {e}")
        return []

def rollback_migration(migration_name: str):
    """
    Remove a migration from the history (for rollback purposes).
    
    Args:
        migration_name (str): Name of the migration to rollback
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        delete_sql = """
        DELETE FROM migration_history 
        WHERE migration_name = :migration_name
        """
        
        db.session.execute(text(delete_sql), {
            'migration_name': migration_name
        })
        db.session.commit()
        logger.info(f"Migration {migration_name} rolled back")
        return True
        
    except Exception as e:
        logger.error(f"Error rolling back migration {migration_name}: {e}")
        db.session.rollback()
        return False