"""
Setup Storage Module

Handles saving parsed trading setups to the database.
This module provides functionality for storing SetupModel instances
and managing setup persistence operations.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import SetupModel
from common.db import db, publish_event
from common.event_constants import EventChannels, EventType

logger = logging.getLogger(__name__)


class SetupStorageService:
    """
    Handles storage operations for trading setups.
    
    This service manages the persistence of parsed trading setups
    and coordinates with the database and event system.
    """
    
    def __init__(self):
        """Initialize setup storage service."""
        self.stats = {
            'total_stored': 0,
            'total_errors': 0,
            'duplicate_count': 0
        }
    
    def store_setup(self, setup: SetupModel) -> bool:
        """
        Store a single trading setup in the database.
        
        Args:
            setup: SetupModel instance to store
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            # Check for duplicates
            if self._is_duplicate_setup(setup):
                logger.info(f"Duplicate setup detected for {setup.ticker}, skipping")
                self.stats['duplicate_count'] += 1
                return False
            
            # Save to database
            db.session.add(setup)
            db.session.commit()
            
            # Update statistics
            self.stats['total_stored'] += 1
            
            # Publish setup stored event
            self._publish_setup_stored_event(setup)
            
            logger.info(f"Successfully stored setup for {setup.ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing setup for {setup.ticker}: {e}")
            db.session.rollback()
            self.stats['total_errors'] += 1
            return False
    
    def store_setup_batch(self, setups: List[SetupModel]) -> Dict[str, Any]:
        """
        Store multiple setups in a batch operation.
        
        Args:
            setups: List of SetupModel instances to store
            
        Returns:
            Dict[str, Any]: Storage results with statistics
        """
        results = {
            'total_submitted': len(setups),
            'successfully_stored': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'stored_setups': []
        }
        
        for setup in setups:
            try:
                if self._is_duplicate_setup(setup):
                    results['duplicates_skipped'] += 1
                    continue
                
                db.session.add(setup)
                results['stored_setups'].append(setup)
                
            except Exception as e:
                logger.error(f"Error preparing setup {setup.ticker} for batch storage: {e}")
                results['errors'] += 1
        
        # Commit all setups at once
        try:
            db.session.commit()
            results['successfully_stored'] = len(results['stored_setups'])
            
            # Publish events for all stored setups
            for setup in results['stored_setups']:
                self._publish_setup_stored_event(setup)
            
            self.stats['total_stored'] += results['successfully_stored']
            
        except Exception as e:
            logger.error(f"Error committing batch setup storage: {e}")
            db.session.rollback()
            results['errors'] += len(results['stored_setups'])
            results['successfully_stored'] = 0
            results['stored_setups'] = []
        
        return results
    
    def update_setup(self, setup_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing setup with new information.
        
        Args:
            setup_id: ID of setup to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            setup = SetupModel.query.get(setup_id)
            if not setup:
                logger.warning(f"Setup {setup_id} not found for update")
                return False
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(setup, field):
                    setattr(setup, field, value)
            
            setup.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Publish update event
            self._publish_setup_updated_event(setup)
            
            logger.info(f"Successfully updated setup {setup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating setup {setup_id}: {e}")
            db.session.rollback()
            return False
    
    def _is_duplicate_setup(self, setup: SetupModel) -> bool:
        """
        Check if a setup is a duplicate of an existing one.
        
        Args:
            setup: SetupModel to check for duplication
            
        Returns:
            bool: True if duplicate exists, False otherwise
        """
        existing = SetupModel.query.filter_by(
            ticker=setup.ticker,
            date=setup.date,
            setup_type=setup.setup_type,
            source_message_id=setup.source_message_id
        ).first()
        
        return existing is not None
    
    def _publish_setup_stored_event(self, setup: SetupModel) -> None:
        """
        Publish event when a setup is stored.
        
        Args:
            setup: SetupModel that was stored
        """
        try:
            event_payload = {
                'setup_id': setup.id,
                'ticker': setup.ticker,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'price_target': setup.price_target,
                'confidence': setup.confidence,
                'date': setup.date.isoformat() if setup.date else None,
                'source_message_id': setup.source_message_id
            }
            
            publish_event(
                event_type=EventType.SETUP_CREATED,
                payload=event_payload,
                channel=EventChannels.SETUP_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error publishing setup stored event: {e}")
    
    def _publish_setup_updated_event(self, setup: SetupModel) -> None:
        """
        Publish event when a setup is updated.
        
        Args:
            setup: SetupModel that was updated
        """
        try:
            event_payload = {
                'setup_id': setup.id,
                'ticker': setup.ticker,
                'updated_at': setup.updated_at.isoformat() if setup.updated_at else None
            }
            
            publish_event(
                event_type=EventType.SETUP_UPDATED,
                payload=event_payload,
                channel=EventChannels.SETUP_UPDATED
            )
            
        except Exception as e:
            logger.error(f"Error publishing setup updated event: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage operation statistics.
        
        Returns:
            Dict[str, Any]: Storage statistics
        """
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset storage statistics."""
        self.stats = {
            'total_stored': 0,
            'total_errors': 0,
            'duplicate_count': 0
        }


def store_setup(setup: SetupModel) -> bool:
    """
    Convenience function to store a single setup.
    
    Args:
        setup: SetupModel instance to store
        
    Returns:
        bool: True if stored successfully, False otherwise
    """
    storage_service = SetupStorageService()
    return storage_service.store_setup(setup)


def store_setups_batch(setups: List[SetupModel]) -> Dict[str, Any]:
    """
    Convenience function to store multiple setups.
    
    Args:
        setups: List of SetupModel instances to store
        
    Returns:
        Dict[str, Any]: Storage results with statistics
    """
    storage_service = SetupStorageService()
    return storage_service.store_setup_batch(setups)