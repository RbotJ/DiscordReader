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
            # Check if message already exists
            existing_message = SetupMessage.get_by_message_id(message_id)
            if existing_message:
                logger.info(f"Message {message_id} already processed")
                return {
                    'message_id': message_id,
                    'ticker_setups_created': len(existing_message.ticker_setups),
                    'signals_created': sum(len(setup.signals) for setup in existing_message.ticker_setups)
                }
            
            # Create setup message record
            setup_message = SetupMessage()
            setup_message.message_id = message_id
            setup_message.channel_id = channel_id
            setup_message.author_id = author_id
            setup_message.content = ""  # Content is processed by parsing slice
            setup_message.source = source
            setup_message.is_processed = False
            setup_message.processing_status = 'processing'
            
            db.session.add(setup_message)
            db.session.commit()
            
            setups_created = 0
            signals_created = 0
            
            # Store the pre-parsed setups
            for setup_data in setups:
                ticker_setup = TickerSetup()
                ticker_setup.setup_message_id = setup_message.id
                ticker_setup.symbol = setup_data.get('symbol')
                ticker_setup.setup_type = setup_data.get('setup_type')
                ticker_setup.direction = setup_data.get('direction')
                ticker_setup.entry_price = setup_data.get('entry_price')
                ticker_setup.target_price = setup_data.get('target_price')
                ticker_setup.stop_loss = setup_data.get('stop_loss')
                ticker_setup.confidence = setup_data.get('confidence')
                ticker_setup.notes = setup_data.get('notes')
                
                db.session.add(ticker_setup)
                db.session.flush()  # Get the ID
                setups_created += 1
                
                # Create signals for this setup
                for signal_data in setup_data.get('signals', []):
                    signal = Signal(
                        ticker_setup_id=ticker_setup.id,
                        signal_type=signal_data['signal_type'],
                        trigger_price=signal_data.get('trigger_price'),
                        target_price=signal_data.get('target_price'),
                        stop_loss=signal_data.get('stop_loss'),
                        confidence=signal_data.get('confidence')
                    )
                    db.session.add(signal)
                    signals_created += 1
            
            # Update message status
            setup_message.is_processed = True
            setup_message.processing_status = 'completed'
            
            db.session.commit()
            
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
            db.session.rollback()
            
            # Update message with error status
            if 'setup_message' in locals():
                setup_message.processing_status = 'error'
                setup_message.error_message = str(e)
                db.session.commit()
            
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