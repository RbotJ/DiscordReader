"""
Database Base Models

Common base classes and shared database configurations for all models.
"""

from datetime import datetime
from .session import db
import logging

# Setup logging
logger = logging.getLogger(__name__)

class BaseModel(db.Model):
    """
    Base model class with common fields and functionality.
    """
    __abstract__ = True
    
    # Common timestamp fields
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def save(self):
        """
        Save the model instance to the database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving {self.__class__.__name__}: {e}")
            db.session.rollback()
            return False
    
    def delete(self):
        """
        Delete the model instance from the database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.__class__.__name__}: {e}")
            db.session.rollback()
            return False
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs):
        """
        Update model instance with provided kwargs.
        
        Args:
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating {self.__class__.__name__}: {e}")
            db.session.rollback()
            return False

class TimestampMixin:
    """
    Mixin for adding timestamp fields to models.
    """
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class SoftDeleteMixin:
    """
    Mixin for adding soft delete functionality.
    """
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)
    
    def soft_delete(self):
        """
        Soft delete the record by setting deleted_at and is_deleted.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.deleted_at = datetime.utcnow()
            self.is_deleted = True
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error soft deleting {self.__class__.__name__}: {e}")
            db.session.rollback()
            return False
    
    def restore(self):
        """
        Restore a soft-deleted record.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.deleted_at = None
            self.is_deleted = False
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error restoring {self.__class__.__name__}: {e}")
            db.session.rollback()
            return False