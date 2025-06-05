"""
Common Database Utilities

Centralized database operations and utilities to eliminate direct SQLAlchemy
imports across slices and provide consistent database access patterns.
"""
import logging
from typing import Optional, Dict, Any, List, Type, TypeVar, Generic
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB
import os

logger = logging.getLogger(__name__)

# Base model for all database models
Base = declarative_base()

# Type variable for generic repository operations
T = TypeVar('T', bound=Base)


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        self.echo = os.environ.get('DB_ECHO', 'false').lower() == 'true'
        self.pool_size = int(os.environ.get('DB_POOL_SIZE', '10'))
        self.max_overflow = int(os.environ.get('DB_MAX_OVERFLOW', '20'))
        self.pool_recycle = int(os.environ.get('DB_POOL_RECYCLE', '3600'))


class DatabaseManager:
    """Centralized database connection and session management."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
        
    def initialize(self):
        """Initialize database connection and session factory."""
        if self._initialized:
            return
            
        try:
            self.engine = create_engine(
                self.config.database_url,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            self._initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
            
    @contextmanager
    def get_session(self):
        """Get a database session with automatic cleanup."""
        if not self._initialized:
            self.initialize()
            
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
            
    def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            self.initialize()
            
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise


class GenericRepository(Generic[T]):
    """Generic repository for common database operations."""
    
    def __init__(self, model_class: Type[T], db_manager: DatabaseManager):
        self.model_class = model_class
        self.db_manager = db_manager
        
    def create(self, **kwargs) -> Optional[T]:
        """Create a new record."""
        try:
            with self.db_manager.get_session() as session:
                instance = self.model_class(**kwargs)
                session.add(instance)
                session.flush()
                session.refresh(instance)
                return instance
        except IntegrityError as e:
            logger.warning(f"Integrity error creating {self.model_class.__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            return None
            
    def get_by_id(self, record_id: Any) -> Optional[T]:
        """Get a record by ID."""
        try:
            with self.db_manager.get_session() as session:
                return session.query(self.model_class).filter(
                    self.model_class.id == record_id
                ).first()
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID {record_id}: {e}")
            return None
            
    def get_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Get a record by a specific field."""
        try:
            with self.db_manager.get_session() as session:
                field = getattr(self.model_class, field_name)
                return session.query(self.model_class).filter(
                    field == value
                ).first()
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by {field_name}: {e}")
            return None
            
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Get all records with optional pagination."""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(self.model_class).offset(offset)
                if limit:
                    query = query.limit(limit)
                return query.all()
        except Exception as e:
            logger.error(f"Error getting all {self.model_class.__name__}: {e}")
            return []
            
    def update(self, record_id: Any, **kwargs) -> Optional[T]:
        """Update a record by ID."""
        try:
            with self.db_manager.get_session() as session:
                instance = session.query(self.model_class).filter(
                    self.model_class.id == record_id
                ).first()
                
                if not instance:
                    return None
                    
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                        
                session.flush()
                session.refresh(instance)
                return instance
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__} {record_id}: {e}")
            return None
            
    def delete(self, record_id: Any) -> bool:
        """Delete a record by ID."""
        try:
            with self.db_manager.get_session() as session:
                instance = session.query(self.model_class).filter(
                    self.model_class.id == record_id
                ).first()
                
                if not instance:
                    return False
                    
                session.delete(instance)
                return True
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__} {record_id}: {e}")
            return False
            
    def exists(self, **kwargs) -> bool:
        """Check if a record exists with given criteria."""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(self.model_class)
                for key, value in kwargs.items():
                    field = getattr(self.model_class, key)
                    query = query.filter(field == value)
                return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking existence in {self.model_class.__name__}: {e}")
            return False
            
    def count(self, **kwargs) -> int:
        """Count records matching criteria."""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(self.model_class)
                for key, value in kwargs.items():
                    field = getattr(self.model_class, key)
                    query = query.filter(field == value)
                return query.count()
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            return 0


# Global database manager instance
_db_manager = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager


def create_repository(model_class: Type[T]) -> GenericRepository[T]:
    """Create a repository for a model class."""
    db_manager = get_database_manager()
    return GenericRepository(model_class, db_manager)


# Common database exceptions for consistent error handling
class DatabaseError(Exception):
    """Base database error."""
    pass


class RecordNotFoundError(DatabaseError):
    """Record not found error."""
    pass


class DuplicateRecordError(DatabaseError):
    """Duplicate record error."""
    pass


# Common database column types for consistent schema
def create_id_column():
    """Create a standard ID column."""
    return Column(Integer, primary_key=True, autoincrement=True)


def create_string_column(length: int = 255, nullable: bool = True, unique: bool = False):
    """Create a standard string column."""
    return Column(String(length), nullable=nullable, unique=unique)


def create_text_column(nullable: bool = True):
    """Create a standard text column."""
    return Column(Text, nullable=nullable)


def create_datetime_column(nullable: bool = True):
    """Create a standard datetime column."""
    return Column(DateTime, nullable=nullable)


def create_boolean_column(default: bool = False, nullable: bool = True):
    """Create a standard boolean column."""
    return Column(Boolean, default=default, nullable=nullable)


def create_json_column(nullable: bool = True):
    """Create a standard JSON column."""
    return Column(JSONB, nullable=nullable)