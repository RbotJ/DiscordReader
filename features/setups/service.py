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
        
    def parse_message_content(
        self, 
        content: str, 
        message_id: str = '', 
        channel_id: str = '', 
        author_id: str = '', 
        source: str = 'unknown'
    ) -> Dict[str, Any]:
        """
        Parse message content and create setup records.
        
        Args:
            content: Message content to parse
            message_id: Discord message ID
            channel_id: Discord channel ID
            author_id: Discord author ID
            source: Source of the message
            
        Returns:
            Dict with parsing results
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
            setup_message = SetupMessage(
                message_id=message_id,
                channel_id=channel_id,
                author_id=author_id,
                content=content,
                source=source,
                is_processed=False,
                processing_status='processing'
            )
            
            db.session.add(setup_message)
            db.session.commit()
            
            # Extract tickers and create setups
            ticker_setups = self._extract_ticker_setups(content)
            setups_created = 0
            signals_created = 0
            
            for ticker_data in ticker_setups:
                ticker_setup = TickerSetup(
                    setup_message_id=setup_message.id,
                    symbol=ticker_data['symbol'],
                    setup_type=ticker_data.get('setup_type'),
                    direction=ticker_data.get('direction'),
                    entry_price=ticker_data.get('entry_price'),
                    target_price=ticker_data.get('target_price'),
                    stop_loss=ticker_data.get('stop_loss'),
                    confidence=ticker_data.get('confidence'),
                    notes=ticker_data.get('notes')
                )
                
                db.session.add(ticker_setup)
                db.session.flush()  # Get the ID
                setups_created += 1
                
                # Create signals for this setup
                for signal_data in ticker_data.get('signals', []):
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
                    'signals_created': signals_created
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
            logger.error(f"Error parsing message content: {e}")
            db.session.rollback()
            
            # Update message with error status
            if 'setup_message' in locals():
                setup_message.processing_status = 'error'
                setup_message.error_message = str(e)
                db.session.commit()
            
            raise
    
    def _extract_ticker_setups(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract ticker setups from message content.
        
        Args:
            content: Message content to parse
            
        Returns:
            List of ticker setup data dictionaries
        """
        import re
        
        ticker_setups = []
        
        # Simple ticker extraction pattern
        ticker_pattern = r'\b([A-Z]{1,5})\b'
        tickers = re.findall(ticker_pattern, content)
        
        # Remove common non-ticker words
        excluded_words = {'THE', 'AND', 'OR', 'BUT', 'FOR', 'WITH', 'THIS', 'THAT', 'FROM', 'TO', 'AT', 'BY', 'UP', 'DOWN', 'IN', 'OUT', 'ON', 'OFF', 'OVER', 'UNDER'}
        tickers = [t for t in tickers if t not in excluded_words and len(t) <= 5]
        
        for ticker in set(tickers):  # Remove duplicates
            # Extract basic setup information for this ticker
            setup_data = {
                'symbol': ticker,
                'setup_type': self._extract_setup_type(content, ticker),
                'direction': self._extract_direction(content, ticker),
                'entry_price': self._extract_price(content, ticker, 'entry'),
                'target_price': self._extract_price(content, ticker, 'target'),
                'stop_loss': self._extract_price(content, ticker, 'stop'),
                'confidence': self._calculate_confidence(content, ticker),
                'signals': self._extract_signals(content, ticker)
            }
            
            # Only include if we found meaningful setup information
            if any([setup_data['setup_type'], setup_data['direction'], 
                   setup_data['entry_price'], setup_data['signals']]):
                ticker_setups.append(setup_data)
        
        return ticker_setups
    
    def _extract_setup_type(self, content: str, ticker: str) -> Optional[str]:
        """Extract setup type from content."""
        content_lower = content.lower()
        
        setup_types = {
            'breakout': ['breakout', 'break out', 'breaking'],
            'pullback': ['pullback', 'pull back', 'retrace'],
            'reversal': ['reversal', 'reverse', 'bounce'],
            'continuation': ['continuation', 'continue', 'trend'],
            'momentum': ['momentum', 'ramp', 'squeeze']
        }
        
        for setup_type, keywords in setup_types.items():
            if any(keyword in content_lower for keyword in keywords):
                return setup_type
        
        return None
    
    def _extract_direction(self, content: str, ticker: str) -> Optional[str]:
        """Extract trade direction from content."""
        content_lower = content.lower()
        
        # Look for directional keywords near the ticker
        for direction, keywords in self._direction_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return direction
        
        return None
    
    def _extract_price(self, content: str, ticker: str, price_type: str) -> Optional[float]:
        """Extract price levels from content."""
        import re
        
        # Simple price pattern - look for numbers that could be prices
        price_pattern = r'\$?(\d+\.?\d*)'
        prices = re.findall(price_pattern, content)
        
        # This is a simplified extraction - in reality, you'd want more
        # sophisticated parsing to associate prices with specific tickers
        # and price types (entry, target, stop)
        
        if prices:
            try:
                return float(prices[0])  # Return first found price as example
            except ValueError:
                pass
        
        return None
    
    def _calculate_confidence(self, content: str, ticker: str) -> float:
        """Calculate confidence score based on setup completeness."""
        score = 0.0
        content_lower = content.lower()
        
        # Check for various confidence indicators
        if any(keyword in content_lower for keyword in self._setup_keywords):
            score += 0.2
        
        if self._extract_direction(content, ticker):
            score += 0.2
        
        if self._extract_price(content, ticker, 'entry'):
            score += 0.2
        
        if self._extract_price(content, ticker, 'target'):
            score += 0.2
        
        if self._extract_price(content, ticker, 'stop'):
            score += 0.2
        
        return min(score, 1.0)
    
    def _extract_signals(self, content: str, ticker: str) -> List[Dict[str, Any]]:
        """Extract trading signals for a ticker."""
        signals = []
        
        # Simple signal extraction - look for common signal patterns
        direction = self._extract_direction(content, ticker)
        if direction:
            signal = {
                'signal_type': direction,
                'trigger_price': self._extract_price(content, ticker, 'trigger'),
                'target_price': self._extract_price(content, ticker, 'target'),
                'stop_loss': self._extract_price(content, ticker, 'stop'),
                'confidence': self._calculate_confidence(content, ticker)
            }
            signals.append(signal)
        
        return signals
    
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