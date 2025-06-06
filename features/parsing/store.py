"""
Parsing Store Module

Handles database operations for the parsing vertical slice.
Provides persistence layer for trade setups and parsed levels.
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker

from common.db import db
from .models import TradeSetup, ParsedLevel
from .parser import ParsedSetupDTO, ParsedLevelDTO

logger = logging.getLogger(__name__)


class ParsingStore:
    """
    Store class for parsing operations.
    Handles all database interactions for trade setups and parsed levels.
    """
    
    def __init__(self):
        """Initialize the parsing store."""
        self.session = db.session
    
    def store_parsed_message(
        self, 
        message_id: str,
        setups: List[ParsedSetupDTO], 
        levels_by_setup: Dict[str, List[ParsedLevelDTO]], 
        trading_day: Optional[date] = None
    ) -> Tuple[List[TradeSetup], List[ParsedLevel]]:
        """
        Store parsed setups and levels from a message.
        
        Args:
            message_id: Discord message ID
            setups: List of parsed setup DTOs
            levels_by_setup: Dict mapping setup ticker to its levels
            trading_day: Trading day (defaults to today)
            
        Returns:
            Tuple of (created_setups, created_levels)
        """
        if trading_day is None:
            trading_day = date.today()
        
        created_setups = []
        created_levels = []
        
        try:
            # Process each setup
            for setup_dto in setups:
                # Check if setup already exists for this message and ticker
                existing_setup = self.get_setup_by_message_and_ticker(message_id, setup_dto.ticker)
                
                if existing_setup:
                    logger.info(f"Setup already exists for {setup_dto.ticker} from message {message_id}")
                    created_setups.append(existing_setup)
                    # Get existing levels
                    existing_levels = ParsedLevel.get_by_setup_id(existing_setup.id)
                    created_levels.extend(existing_levels)
                    continue
                
                # Create new setup
                new_setup = TradeSetup(
                    message_id=message_id,
                    ticker=setup_dto.ticker,
                    trading_day=trading_day,
                    setup_type=setup_dto.setup_type,
                    bias_note=setup_dto.bias_note,
                    direction=setup_dto.direction,
                    confidence_score=setup_dto.confidence_score,
                    raw_content=setup_dto.raw_content,
                    parsed_metadata=setup_dto.parsed_metadata,
                    active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.session.add(new_setup)
                self.session.flush()  # Get the ID
                
                created_setups.append(new_setup)
                logger.info(f"Created setup {new_setup.id} for {setup_dto.ticker}")
                
                # Create levels for this setup
                setup_levels = levels_by_setup.get(setup_dto.ticker, [])
                for level_dto in setup_levels:
                    new_level = ParsedLevel(
                        setup_id=new_setup.id,
                        level_type=level_dto.level_type,
                        direction=level_dto.direction,
                        trigger_price=level_dto.trigger_price,
                        strategy=level_dto.strategy,
                        confidence=level_dto.confidence,
                        description=level_dto.description,
                        level_metadata={},  # Can be expanded later
                        active=True,
                        triggered=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    self.session.add(new_level)
                    created_levels.append(new_level)
                
                logger.info(f"Created {len(setup_levels)} levels for setup {new_setup.id}")
            
            # Commit all changes
            self.session.commit()
            logger.info(f"Successfully stored {len(created_setups)} setups and {len(created_levels)} levels")
            
            return created_setups, created_levels
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error storing parsed message: {e}")
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error storing parsed message: {e}")
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error storing parsed message: {e}")
            raise
    
    def get_setup_by_message_and_ticker(self, message_id: str, ticker: str) -> Optional[TradeSetup]:
        """Get setup by message ID and ticker."""
        try:
            return self.session.query(TradeSetup).filter_by(
                message_id=message_id,
                ticker=ticker.upper()
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error querying setup by message and ticker: {e}")
            return None
    
    def get_setups_by_message(self, message_id: str) -> List[TradeSetup]:
        """Get all setups created from a specific message."""
        try:
            return self.session.query(TradeSetup).filter_by(message_id=message_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Error querying setups by message: {e}")
            return []
    
    def get_active_setups_for_day(self, trading_day: Optional[date] = None) -> List[TradeSetup]:
        """Get active setups for a specific trading day."""
        if trading_day is None:
            trading_day = date.today()
        
        try:
            return self.session.query(TradeSetup).filter_by(
                trading_day=trading_day,
                active=True
            ).order_by(TradeSetup.created_at.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Error querying active setups for day: {e}")
            return []
    
    def get_levels_by_setup(self, setup_id: int) -> List[ParsedLevel]:
        """Get all levels for a specific setup."""
        try:
            return self.session.query(ParsedLevel).filter_by(
                setup_id=setup_id,
                active=True
            ).order_by(ParsedLevel.created_at).all()
        except SQLAlchemyError as e:
            logger.error(f"Error querying levels by setup: {e}")
            return []
    
    def update_setup_confidence(self, setup_id: int, new_confidence: float) -> bool:
        """Update confidence score for a setup."""
        try:
            setup = self.session.query(TradeSetup).filter_by(id=setup_id).first()
            if setup:
                setup.confidence_score = new_confidence
                setup.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Updated confidence for setup {setup_id} to {new_confidence}")
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating setup confidence: {e}")
            return False
    
    def deactivate_setup(self, setup_id: int) -> bool:
        """Deactivate a setup and its levels."""
        try:
            setup = self.session.query(TradeSetup).filter_by(id=setup_id).first()
            if setup:
                setup.active = False
                setup.updated_at = datetime.utcnow()
                
                # Deactivate associated levels
                levels = self.session.query(ParsedLevel).filter_by(setup_id=setup_id).all()
                for level in levels:
                    level.active = False
                    level.updated_at = datetime.utcnow()
                
                self.session.commit()
                logger.info(f"Deactivated setup {setup_id} and its {len(levels)} levels")
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error deactivating setup: {e}")
            return False
    
    def trigger_level(self, level_id: int) -> bool:
        """Mark a level as triggered."""
        try:
            level = self.session.query(ParsedLevel).filter_by(id=level_id).first()
            if level:
                level.triggered = True
                level.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Triggered level {level_id}")
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error triggering level: {e}")
            return False
    
    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get statistics about parsed data."""
        try:
            total_setups = self.session.query(TradeSetup).count()
            active_setups = self.session.query(TradeSetup).filter_by(active=True).count()
            total_levels = self.session.query(ParsedLevel).count()
            active_levels = self.session.query(ParsedLevel).filter_by(active=True, triggered=False).count()
            triggered_levels = self.session.query(ParsedLevel).filter_by(triggered=True).count()
            
            # Today's stats
            today = date.today()
            today_setups = self.session.query(TradeSetup).filter_by(trading_day=today).count()
            today_active_setups = self.session.query(TradeSetup).filter_by(
                trading_day=today, active=True
            ).count()
            
            return {
                'total_setups': total_setups,
                'active_setups': active_setups,
                'total_levels': total_levels,
                'active_levels': active_levels,
                'triggered_levels': triggered_levels,
                'today_setups': today_setups,
                'today_active_setups': today_active_setups,
                'setup_activation_rate': round((active_setups / total_setups * 100), 2) if total_setups > 0 else 0,
                'level_trigger_rate': round((triggered_levels / total_levels * 100), 2) if total_levels > 0 else 0
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting parsing statistics: {e}")
            return {}


# Global store instance
_store = None

def get_parsing_store() -> ParsingStore:
    """Get the global parsing store instance."""
    global _store
    if _store is None:
        _store = ParsingStore()
    return _store