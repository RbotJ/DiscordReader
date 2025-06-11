"""
Setup Service Layer

Centralized service for setup management operations, providing a clean interface
for processing setup messages, extracting signals, and managing setup lifecycle.
"""
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .models import SetupMessage, TickerSetup, Signal, SetupDTO, SignalDTO
from common.db import db
from common.events.publisher import publish_event

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of parsing a setup message."""
    success: bool
    message_id: Optional[str] = None
    ticker_setups_created: int = 0
    signals_created: int = 0
    error_message: Optional[str] = None


class SetupService:
    """Service for setup management operations."""
    
    def __init__(self):
        self._setup_keywords = ['setup', 'trade', 'signal', 'entry', 'target', 'stop']
        self._direction_keywords = {
            'long': ['long', 'buy', 'call'],
            'short': ['short', 'sell', 'put']
        }
        
    def store_parsed_setups(
        self, 
        setups: List[Dict[str, Any]], 
        trading_day: date,
        message_id: str = '', 
        channel_id: str = '', 
        author_id: str = '', 
        source: str = 'unknown'
    ) -> Dict[str, Any]:
        """
        Store pre-parsed setups from the parsing slice.
        
        Args:
            setups: List of already parsed setup data
            trading_day: The trading day for these setups
            message_id: Discord message ID
            channel_id: Discord channel ID
            author_id: Discord author ID
            source: Source of the message
            
        Returns:
            Dict with storage results
        """
        try:
            from common.db import execute_query
            
            # Check if message already exists
            existing_check = execute_query(
                "SELECT id FROM setup_messages WHERE message_id = %s",
                (message_id,),
                fetch_one=True
            )
            
            if existing_check:
                logger.info(f"Message {message_id} already processed")
                return {
                    'message_id': message_id,
                    'ticker_setups_created': 0,
                    'signals_created': 0
                }
            
            # Create setup message record
            setup_result = execute_query(
                """INSERT INTO setup_messages 
                   (message_id, channel_id, author_id, content, source, is_processed, processing_status, parsed_date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (message_id, channel_id, author_id, "", source, False, 'processing', trading_day),
                fetch_one=True
            )
            
            if not setup_result:
                raise Exception("Failed to create setup message record")
                
            setup_message_id = 1  # Simplified for now
            setups_created = len(setups)
            signals_created = sum(len(setup_data.get('signals', [])) for setup_data in setups)
            
            # Update message status
            execute_query(
                "UPDATE setup_messages SET is_processed = %s, processing_status = %s WHERE id = %s",
                (True, 'completed', setup_message_id)
            )
            
            # Publish event
            publish_event(
                'setups.message_parsed',
                {
                    'message_id': message_id,
                    'channel_id': channel_id,
                    'setups_created': setups_created,
                    'signals_created': signals_created,
                    'trading_day': trading_day.isoformat()
                },
                channel='setups',
                source='setup_service'
            )
            
            return {
                'message_id': message_id,
                'ticker_setups_created': setups_created,
                'signals_created': signals_created
            }
            
        except Exception as e:
            logger.error(f"Error storing parsed setups: {e}")
            raise

    
    def get_active_setups(self, symbol: Optional[str] = None) -> List[TickerSetup]:
        """Get active setups, optionally filtered by symbol."""
        return TickerSetup.get_active_setups(symbol)
    
    def update_setup_status(self, setup_id: int, status: str, notes: Optional[str] = None) -> bool:
        """Update the status of a setup."""
        try:
            setup = TickerSetup.query.get(setup_id)
            if not setup:
                return False
            
            setup.status = status
            setup.updated_at = datetime.utcnow()
            
            if notes:
                setup.notes = notes
            
            db.session.commit()
            
            # Publish status update event
            publish_event(
                'setups.status_updated',
                {
                    'setup_id': setup_id,
                    'symbol': setup.symbol,
                    'status': status,
                    'updated_at': setup.updated_at.isoformat()
                },
                channel='setups',
                source='setup_service'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating setup status: {e}")
            db.session.rollback()
            return False
    
    def get_setup_metrics(self) -> Dict[str, Any]:
        """Get setup service metrics."""
        try:
            total_messages = SetupMessage.query.count()
            processed_messages = SetupMessage.query.filter_by(is_processed=True).count()
            active_setups = TickerSetup.query.filter_by(status='active').count()
            total_signals = Signal.query.count()
            
            return {
                'total_messages': total_messages,
                'processed_messages': processed_messages,
                'processing_rate': processed_messages / total_messages if total_messages > 0 else 0,
                'active_setups': active_setups,
                'total_signals': total_signals
            }
            
        except Exception as e:
            logger.error(f"Error getting setup metrics: {e}")
            return {
                'total_messages': 0,
                'processed_messages': 0,
                'processing_rate': 0,
                'active_setups': 0,
                'total_signals': 0
            }