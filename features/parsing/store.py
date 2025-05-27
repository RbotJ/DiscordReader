` tags.

```
<replit_final_file>
"""
Setup Storage Service Module

Handles storing parsed trading setups to the database.
This module provides a clean interface for persisting SetupModel instances
and managing setup lifecycle operations.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import SetupModel
from common.db import db

logger = logging.getLogger(__name__)


class SetupStorageService:
    """
    Service for storing and managing trading setups in the database.

    This service handles the persistence layer for parsed trading setups,
    providing methods to store, update, and query setup data.
    """

    def __init__(self):
        """Initialize the storage service."""
        self.stats = {
            'setups_stored': 0,
            'storage_errors': 0,
            'last_storage_time': None
        }

    def store_setup(self, setup: SetupModel) -> Optional[SetupModel]:
        """
        Store a single setup in the database.

        Args:
            setup: SetupModel instance to store

        Returns:
            Optional[SetupModel]: Stored setup with ID or None if failed
        """
        try:
            # Add to session and commit
            db.session.add(setup)
            db.session.commit()

            # Update stats
            self.stats['setups_stored'] += 1
            self.stats['last_storage_time'] = datetime.utcnow()

            logger.info(f"Successfully stored setup {setup.id} for {setup.ticker}")
            return setup

        except Exception as e:
            logger.error(f"Error storing setup for {setup.ticker}: {e}")
            db.session.rollback()
            self.stats['storage_errors'] += 1
            return None

    def store_setup_batch(self, setups: List[SetupModel]) -> Dict[str, Any]:
        """
        Store multiple setups in a single transaction.

        Args:
            setups: List of SetupModel instances to store

        Returns:
            Dict[str, Any]: Results including counts and stored setups
        """
        stored_setups = []
        failed_setups = []

        try:
            # Add all setups to session
            for setup in setups:
                db.session.add(setup)

            # Commit all at once
            db.session.commit()
            stored_setups = setups

            # Update stats
            self.stats['setups_stored'] += len(stored_setups)
            self.stats['last_storage_time'] = datetime.utcnow()

            logger.info(f"Successfully stored {len(stored_setups)} setups")

        except Exception as e:
            logger.error(f"Error storing setup batch: {e}")
            db.session.rollback()
            failed_setups = setups
            self.stats['storage_errors'] += len(failed_setups)

        return {
            'successfully_stored': len(stored_setups),
            'failed_to_store': len(failed_setups),
            'stored_setups': stored_setups,
            'failed_setups': failed_setups
        }

    def update_setup(self, setup: SetupModel) -> bool:
        """
        Update an existing setup in the database.

        Args:
            setup: SetupModel instance to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            setup.updated_at = datetime.utcnow()
            db.session.commit()

            logger.debug(f"Successfully updated setup {setup.id}")
            return True

        except Exception as e:
            logger.error(f"Error updating setup {setup.id}: {e}")
            db.session.rollback()
            self.stats['storage_errors'] += 1
            return False

    def get_setup_by_id(self, setup_id: int) -> Optional[SetupModel]:
        """
        Retrieve a setup by its ID.

        Args:
            setup_id: Setup ID to retrieve

        Returns:
            Optional[SetupModel]: Setup if found, None otherwise
        """
        try:
            return SetupModel.query.get(setup_id)
        except Exception as e:
            logger.error(f"Error retrieving setup {setup_id}: {e}")
            return None

    def get_setups_by_message(self, message_id: str) -> List[SetupModel]:
        """
        Get all setups created from a specific message.

        Args:
            message_id: Discord message ID

        Returns:
            List[SetupModel]: Setups from the specified message
        """
        try:
            return SetupModel.query.filter_by(
                source_message_id=message_id
            ).all()
        except Exception as e:
            logger.error(f"Error retrieving setups for message {message_id}: {e}")
            return []

    def get_active_setups(self, ticker: Optional[str] = None) -> List[SetupModel]:
        """
        Get active setups, optionally filtered by ticker.

        Args:
            ticker: Optional ticker to filter by

        Returns:
            List[SetupModel]: Active setups
        """
        try:
            query = SetupModel.query.filter_by(active=True, executed=False)
            if ticker:
                query = query.filter_by(ticker=ticker.upper())
            return query.order_by(SetupModel.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error retrieving active setups: {e}")
            return []

    def deactivate_setup(self, setup_id: int) -> bool:
        """
        Deactivate a setup by ID.

        Args:
            setup_id: Setup ID to deactivate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            setup = SetupModel.query.get(setup_id)
            if setup:
                setup.deactivate()
                db.session.commit()
                logger.info(f"Deactivated setup {setup_id}")
                return True
            else:
                logger.warning(f"Setup {setup_id} not found for deactivation")
                return False
        except Exception as e:
            logger.error(f"Error deactivating setup {setup_id}: {e}")
            db.session.rollback()
            return False

    def mark_setup_executed(self, setup_id: int, execution_price: Optional[float] = None) -> bool:
        """
        Mark a setup as executed.

        Args:
            setup_id: Setup ID to mark as executed
            execution_price: Optional execution price

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            setup = SetupModel.query.get(setup_id)
            if setup:
                setup.mark_as_executed(execution_price)
                db.session.commit()
                logger.info(f"Marked setup {setup_id} as executed")
                return True
            else:
                logger.warning(f"Setup {setup_id} not found for execution marking")
                return False
        except Exception as e:
            logger.error(f"Error marking setup {setup_id} as executed: {e}")
            db.session.rollback()
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage service statistics.

        Returns:
            Dict[str, Any]: Storage statistics
        """
        return {
            'service_stats': self.stats.copy(),
            'database_stats': SetupModel.get_setup_statistics(),
            'timestamp': datetime.utcnow().isoformat()
        }

    def reset_stats(self) -> None:
        """Reset storage service statistics."""
        self.stats = {
            'setups_stored': 0,
            'storage_errors': 0,
            'last_storage_time': None
        }


# Convenience functions for direct usage
def store_parsed_setup(setup: SetupModel) -> Optional[SetupModel]:
    """
    Convenience function to store a single parsed setup.

    Args:
        setup: SetupModel to store

    Returns:
        Optional[SetupModel]: Stored setup or None if failed
    """
    service = SetupStorageService()
    return service.store_setup(setup)


def store_parsed_setups(setups: List[SetupModel]) -> Dict[str, Any]:
    """
    Convenience function to store multiple parsed setups.

    Args:
        setups: List of SetupModel instances to store

    Returns:
        Dict[str, Any]: Storage results
    """
    service = SetupStorageService()
    return service.store_setup_batch(setups)