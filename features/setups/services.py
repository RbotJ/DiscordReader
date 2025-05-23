"""
Setup Message Service

Unified service for handling setup message operations, consolidating the 
duplicate save_setup_message functions from multiple repository files.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import asdict

from common.models import TradeSetupMessage, TickerSetupData
from common.db import db, publish_event
from common.models_db import SetupMessageModel, TickerSetupModel

logger = logging.getLogger(__name__)


class SetupMessageService:
    """
    Centralized service for setup message operations.
    
    Consolidates functionality from:
    - repository_fixed.py
    - repository_adapter.py  
    - multi_ticker_adapter.py
    - setup_adapter.py
    """
    
    @staticmethod
    def save_message(
        setup_message: TradeSetupMessage,
        ticker_setups: Optional[List[TickerSetupData]] = None,
        publish_events: bool = True
    ) -> int:
        """
        Save a setup message and associated ticker setups to the database.
        
        Args:
            setup_message: The main setup message to save
            ticker_setups: Optional list of ticker setup data
            publish_events: Whether to publish events for this save operation
            
        Returns:
            ID of the saved setup message
            
        Raises:
            Exception: If database operation fails
        """
        try:
            # Create the main setup message record
            message_model = SetupMessageModel(
                message_id=setup_message.message_id,
                source=setup_message.channel_id or 'unknown',
                raw_text=setup_message.content,
                parsed_data=asdict(setup_message) if hasattr(setup_message, '__dict__') else {},
                date=setup_message.date,
                created_at=setup_message.timestamp
            )
            
            db.session.add(message_model)
            db.session.flush()  # Get the ID
            
            # Save associated ticker setups if provided
            if ticker_setups:
                for ticker_setup in ticker_setups:
                    ticker_model = TickerSetupModel(
                        symbol=ticker_setup.ticker,
                        setup_message_id=message_model.id,
                        text=ticker_setup.setup_type,
                        category=ticker_setup.setup_type,
                        direction=ticker_setup.direction,
                        price_level=ticker_setup.price_target,
                        status='active' if ticker_setup.active else 'inactive',
                        created_at=ticker_setup.created_at
                    )
                    db.session.add(ticker_model)
            
            db.session.commit()
            
            # Publish events if requested
            if publish_events:
                SetupMessageService._publish_save_events(
                    message_model.id, 
                    setup_message, 
                    ticker_setups or []
                )
            
            logger.info(f"Successfully saved setup message {setup_message.message_id} with ID {message_model.id}")
            return message_model.id
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save setup message {setup_message.message_id}: {e}")
            raise
    
    @staticmethod
    def get_message(message_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a setup message by message ID.
        
        Args:
            message_id: The message ID to lookup
            
        Returns:
            Dictionary representation of the message, or None if not found
        """
        try:
            message = SetupMessageModel.query.filter_by(message_id=message_id).first()
            
            if not message:
                return None
            
            # Include associated ticker setups
            ticker_setups = TickerSetupModel.query.filter_by(
                setup_message_id=message.id
            ).all()
            
            return {
                'id': message.id,
                'message_id': message.message_id,
                'source': message.source,
                'raw_text': message.raw_text,
                'parsed_data': message.parsed_data,
                'date': message.date,
                'created_at': message.created_at,
                'ticker_setups': [
                    {
                        'symbol': ts.symbol,
                        'category': ts.category,
                        'direction': ts.direction,
                        'price_level': ts.price_level,
                        'status': ts.status,
                        'created_at': ts.created_at
                    }
                    for ts in ticker_setups
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve setup message {message_id}: {e}")
            return None
    
    @staticmethod
    def get_recent_messages(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent setup messages.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = SetupMessageModel.query.order_by(
                SetupMessageModel.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': msg.id,
                    'message_id': msg.message_id,
                    'source': msg.source,
                    'raw_text': msg.raw_text[:200] + '...' if len(msg.raw_text) > 200 else msg.raw_text,
                    'date': msg.date,
                    'created_at': msg.created_at,
                    'ticker_count': TickerSetupModel.query.filter_by(setup_message_id=msg.id).count()
                }
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent messages: {e}")
            return []
    
    @staticmethod
    def update_message_status(message_id: str, status: str) -> bool:
        """
        Update the status of a setup message.
        
        Args:
            message_id: The message ID to update
            status: New status value
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            message = SetupMessageModel.query.filter_by(message_id=message_id).first()
            
            if not message:
                logger.warning(f"Setup message {message_id} not found for status update")
                return False
            
            # Update parsed_data with status
            if message.parsed_data:
                message.parsed_data['status'] = status
            else:
                message.parsed_data = {'status': status}
            
            db.session.commit()
            
            # Publish status update event
            publish_event('setup_message_status_updated', {
                'message_id': message_id,
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Updated status for setup message {message_id} to {status}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update status for setup message {message_id}: {e}")
            return False
    
    @staticmethod
    def _publish_save_events(
        message_db_id: int, 
        setup_message: TradeSetupMessage, 
        ticker_setups: List[TickerSetupData]
    ):
        """
        Publish events related to saving setup messages.
        
        Args:
            message_db_id: Database ID of the saved message
            setup_message: The original setup message
            ticker_setups: Associated ticker setups
        """
        try:
            # Publish main message saved event
            publish_event('setup_message_saved', {
                'db_id': message_db_id,
                'message_id': setup_message.message_id,
                'source': setup_message.channel_id or 'unknown',
                'ticker_count': len(ticker_setups),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Publish ticker setup events
            for ticker_setup in ticker_setups:
                publish_event('ticker_setup_created', {
                    'ticker': ticker_setup.ticker,
                    'setup_type': ticker_setup.setup_type,
                    'direction': ticker_setup.direction,
                    'price_target': ticker_setup.price_target,
                    'confidence': ticker_setup.confidence,
                    'message_id': setup_message.message_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Failed to publish save events for message {setup_message.message_id}: {e}")
            # Don't raise - event publishing failures shouldn't break the save operation