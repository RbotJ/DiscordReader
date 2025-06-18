"""
Duplicate Detection Module

Provides isolated duplicate detection logic for trade setups without disrupting
the core parsing pipeline. Implements configurable policies for handling duplicates.
"""

import logging
import os
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from common.db import db
from .models import TradeSetup

logger = logging.getLogger(__name__)

# Configurable duplicate detection policy
DUPLICATE_POLICY = os.getenv("DUPLICATE_POLICY", "skip")  # Options: skip, replace, allow


class DuplicateDetector:
    """
    Isolated duplicate detection logic for trade setups.
    
    This class provides pure functions for duplicate detection without
    side effects on the main parsing pipeline.
    """
    
    def __init__(self, policy: str = DUPLICATE_POLICY):
        """
        Initialize duplicate detector.
        
        Args:
            policy: Duplicate handling policy (skip, replace, allow)
        """
        self.policy = policy
        
    def check_for_duplicate(self, session: Session, trading_day: date, 
                          current_msg_id: str) -> Optional[Tuple[str, datetime, int]]:
        """
        Check if there's already a parsed message for this trading day.
        
        Args:
            session: Database session
            trading_day: The trading day to check
            current_msg_id: Current message ID to exclude from duplicate check
            
        Returns:
            Tuple of (message_id, timestamp, content_length) if duplicate found, None otherwise
        """
        try:
            # Find existing setup for this trading day from a different message
            existing_setup = session.query(TradeSetup).filter(
                TradeSetup.trading_day == trading_day,
                TradeSetup.message_id != current_msg_id
            ).first()
            
            if existing_setup:
                # Get message details from the ingestion system
                from features.ingestion.store import get_ingestion_store
                ingestion_store = get_ingestion_store()
                
                message_details = ingestion_store.get_message_by_id(existing_setup.message_id)
                if message_details:
                    return (
                        existing_setup.message_id,
                        message_details.get('timestamp'),
                        len(message_details.get('content', ''))
                    )
                    
            return None
            
        except Exception as e:
            logger.error(f"Error checking for duplicates on {trading_day}: {e}")
            return None
    
    def should_skip_duplicate(self, session: Session, trading_day: date, 
                            current_msg_id: str) -> bool:
        """
        Determine if processing should be skipped due to duplicate detection.
        
        Args:
            session: Database session
            trading_day: Trading day to check
            current_msg_id: Current message ID
            
        Returns:
            True if processing should be skipped
        """
        if self.policy != "skip":
            return False
            
        duplicate_info = self.check_for_duplicate(session, trading_day, current_msg_id)
        if duplicate_info:
            existing_msg_id, _, _ = duplicate_info
            logger.info(f"Policy 'skip': Skipping duplicate message {current_msg_id} for trading day {trading_day} (existing: {existing_msg_id})")
            return True
            
        return False
    
    def should_replace_existing(self, session: Session, trading_day: date,
                              current_msg_id: str, current_timestamp: datetime,
                              current_content_length: int) -> bool:
        """
        Determine if existing setups should be replaced with current message.
        
        Args:
            session: Database session
            trading_day: Trading day to check
            current_msg_id: Current message ID
            current_timestamp: Current message timestamp
            current_content_length: Current message content length
            
        Returns:
            True if existing setups should be replaced
        """
        if self.policy != "replace":
            return False
            
        duplicate_info = self.check_for_duplicate(session, trading_day, current_msg_id)
        if not duplicate_info:
            return False  # No duplicate found
            
        existing_msg_id, existing_timestamp, existing_length = duplicate_info
        
        # Replace if new message is newer and longer (better quality)
        if (current_timestamp > existing_timestamp and 
            current_content_length > existing_length):
            logger.info(f"Policy 'replace': New message {current_msg_id} is newer and longer, replacing existing {existing_msg_id}")
            return True
        else:
            logger.info(f"Policy 'replace': Existing message {existing_msg_id} is preferred over {current_msg_id}")
            return False
    
    def delete_existing_setups(self, session: Session, trading_day: date) -> int:
        """
        Delete existing setups for a trading day.
        
        Args:
            session: Database session
            trading_day: Trading day to clear
            
        Returns:
            Number of setups deleted
        """
        try:
            # Delete all setups for this trading day
            deleted_count = session.query(TradeSetup).filter(
                TradeSetup.trading_day == trading_day
            ).delete()
            
            logger.info(f"Deleted {deleted_count} existing setups for trading day {trading_day}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting existing setups for {trading_day}: {e}")
            return 0
    
    def get_duplicate_action(self, session: Session, trading_day: date,
                           current_msg_id: str, current_timestamp: datetime,
                           current_content_length: int) -> str:
        """
        Get the action to take based on duplicate detection policy.
        
        Args:
            session: Database session
            trading_day: Trading day to check
            current_msg_id: Current message ID
            current_timestamp: Current message timestamp
            current_content_length: Current message content length
            
        Returns:
            Action string: "proceed", "skip", "replace"
        """
        try:
            duplicate_info = self.check_for_duplicate(session, trading_day, current_msg_id)
            if not duplicate_info:
                return "proceed"  # No duplicate found
            
            existing_msg_id, existing_timestamp, existing_length = duplicate_info
            logger.info(f"Duplicate detected for trading day {trading_day}: existing {existing_msg_id} vs new {current_msg_id}")
            
            if self.policy == "skip":
                return "skip"
            elif self.policy == "allow":
                logger.info(f"Policy 'allow': Processing duplicate message {current_msg_id} with flag")
                return "proceed"
            elif self.policy == "replace":
                if self.should_replace_existing(session, trading_day, current_msg_id, 
                                              current_timestamp, current_content_length):
                    return "replace"
                else:
                    return "skip"
            else:
                logger.warning(f"Unknown duplicate policy '{self.policy}', defaulting to proceed")
                return "proceed"
                
        except Exception as e:
            logger.error(f"Error in duplicate detection for message {current_msg_id}: {e}")
            return "proceed"  # Default to processing on error
    
    def get_duplicate_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Get statistics about duplicate trading days.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with duplicate statistics
        """
        try:
            # Count duplicate trading days
            from sqlalchemy import func
            
            duplicate_days = session.query(
                TradeSetup.trading_day,
                func.count(func.distinct(TradeSetup.message_id)).label('message_count')
            ).group_by(TradeSetup.trading_day).having(
                func.count(func.distinct(TradeSetup.message_id)) > 1
            ).all()
            
            return {
                'duplicate_trading_days': len(duplicate_days),
                'duplicate_days_list': [
                    {
                        'trading_day': day.strftime('%Y-%m-%d'),
                        'message_count': count
                    }
                    for day, count in duplicate_days[:10]  # Show first 10
                ],
                'current_policy': self.policy
            }
            
        except Exception as e:
            logger.error(f"Error getting duplicate statistics: {e}")
            return {
                'duplicate_trading_days': 0,
                'duplicate_days_list': [],
                'current_policy': self.policy
            }


def get_duplicate_detector(policy: str = DUPLICATE_POLICY) -> DuplicateDetector:
    """
    Get a duplicate detector instance.
    
    Args:
        policy: Duplicate handling policy
        
    Returns:
        DuplicateDetector instance
    """
    return DuplicateDetector(policy)