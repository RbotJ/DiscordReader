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
from sqlalchemy import text

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
        trading_day: Optional[date] = None,
        aplus_setups: Optional[List] = None
    ) -> Tuple[List[TradeSetup], List[ParsedLevel]]:
        """
        Store parsed setups and levels from a message.
        
        Args:
            message_id: Discord message ID
            setups: List of parsed setup DTOs
            levels_by_setup: Dict mapping setup ticker to its levels
            trading_day: Trading day (defaults to today)
            aplus_setups: List of enhanced A+ setup DTOs with profile names
            
        Returns:
            Tuple of (created_setups, created_levels)
        """
        if trading_day is None:
            trading_day = date.today()
        
        created_setups = []
        created_levels = []
        
        try:
            # Process A+ setups with enhanced schema fields
            if aplus_setups:
                logger.info(f"Processing {len(aplus_setups)} A+ setups for message {message_id}")
                for i, setup_dto in enumerate(aplus_setups):
                    logger.info(f"Processing setup {i+1}/{len(aplus_setups)}: {setup_dto.ticker} {setup_dto.profile_name}")
                    # Remove duplicate check to allow multiple setups per ticker per message
                    # Each individual setup line should create its own trade setup entry
                    
                    try:
                        # Create new enhanced setup with profile name and trigger level
                        new_setup = TradeSetup()
                        new_setup.message_id = message_id
                        new_setup.ticker = setup_dto.ticker
                        new_setup.trading_day = trading_day
                        new_setup.setup_type = setup_dto.setup_type
                        new_setup.profile_name = setup_dto.profile_name
                        new_setup.direction = setup_dto.direction
                        new_setup.trigger_level = setup_dto.trigger_level
                        new_setup.entry_condition = setup_dto.entry_condition
                        new_setup.raw_content = setup_dto.raw_line
                        new_setup.parsed_metadata = {
                            'source': 'aplus_parser',
                            'setup_strategy': setup_dto.strategy,
                            'target_count': len(setup_dto.target_prices)
                        }
                        new_setup.active = True
                        
                        db.session.add(new_setup)
                        db.session.flush()  # Get the ID
                        created_setups.append(new_setup)
                        
                        # Create target levels for each price
                        for i, target_price in enumerate(setup_dto.target_prices):
                            try:
                                from datetime import datetime
                                level = ParsedLevel(
                                    setup_id=new_setup.id,
                                    level_type='target',
                                    direction=setup_dto.direction,
                                    trigger_price=target_price,
                                    sequence_order=i + 1,
                                    strategy=setup_dto.strategy,
                                    description=f"Target {i + 1} for {setup_dto.ticker}",
                                    active=True,
                                    triggered=False,
                                    created_at=datetime.utcnow(),
                                    updated_at=datetime.utcnow()
                                )
                                
                                db.session.add(level)
                                created_levels.append(level)
                                logger.debug(f"Created level {i+1} with price {target_price} for setup {new_setup.id}")
                            except Exception as e:
                                logger.error(f"Error creating level {i+1} for setup {new_setup.id}: {e}")
                                # Don't rollback here - just skip this level
                                continue
                    except Exception as e:
                        logger.error(f"Error creating setup for {setup_dto.ticker}: {e}")
                        # Don't rollback here - just skip this setup
                        continue
            
            # Process standard setups if provided
            elif setups:
                for setup_dto in setups:
                    # Allow multiple setups per ticker per message
                    
                    # Create new standard setup
                    new_setup = TradeSetup()
                    new_setup.message_id = message_id
                    new_setup.ticker = setup_dto.ticker
                    new_setup.trading_day = trading_day
                    new_setup.setup_type = setup_dto.setup_type
                    new_setup.bias_note = setup_dto.bias_note
                    new_setup.direction = setup_dto.direction
                    new_setup.confidence_score = setup_dto.confidence_score
                    new_setup.raw_content = setup_dto.raw_content
                    new_setup.parsed_metadata = setup_dto.parsed_metadata
                    new_setup.active = True
                
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

    def get_unparsed_messages(self, channel_id: Optional[str] = None, 
                            since_timestamp: Optional[str] = None,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages that haven't been parsed yet.
        
        Args:
            channel_id: Optional channel filter
            since_timestamp: Optional timestamp to start from
            limit: Maximum number of messages to return
            
        Returns:
            List of unparsed message dictionaries
        """
        try:
            # Build query conditions
            conditions = ["dm.message_id NOT IN (SELECT DISTINCT message_id FROM trade_setups WHERE message_id IS NOT NULL)"]
            params = {'limit': limit}
            
            if channel_id:
                conditions.append("dm.channel_id = :channel_id")
                params['channel_id'] = channel_id
                
            if since_timestamp:
                conditions.append("dm.timestamp >= :since_timestamp")
                params['since_timestamp'] = since_timestamp
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
            SELECT dm.message_id, dm.channel_id, dm.content, dm.author_id, dm.timestamp
            FROM discord_messages dm
            WHERE {where_clause}
            ORDER BY dm.timestamp DESC
            LIMIT :limit
            """
            
            messages = self.session.execute(text(query), params).fetchall()
            return [dict(msg._mapping) for msg in messages]
                
        except Exception as e:
            logger.error(f"Error getting unparsed messages: {e}")
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
    
    def get_available_trading_days(self) -> List[date]:
        """Get list of distinct trading days that have active setups."""
        try:
            from sqlalchemy import distinct
            days = self.session.query(distinct(TradeSetup.trading_day)).filter_by(
                active=True
            ).order_by(TradeSetup.trading_day.desc()).all()
            return [day[0] for day in days if day[0] is not None]
        except SQLAlchemyError as e:
            logger.error(f"Error querying available trading days: {e}")
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

    def get_audit_anomalies(self) -> Dict[str, Any]:
        """Get audit data for anomalies in trade setup dates and data quality."""
        try:
            # Find setups on non-trading days (weekends)
            weekend_setups = []
            all_setups = self.session.query(TradeSetup).filter_by(active=True).all()
            
            for setup in all_setups:
                if setup.trading_day and setup.trading_day.weekday() >= 5:  # Saturday=5, Sunday=6
                    weekend_setups.append({
                        'id': setup.id,
                        'ticker': setup.ticker,
                        'trading_day': setup.trading_day.isoformat(),
                        'weekday': setup.trading_day.strftime('%A'),
                        'message_id': setup.message_id,
                        'setup_type': setup.setup_type,
                        'profile_name': setup.profile_name
                    })
            
            # Find dates that appear to be current date (possible parsing failures)
            today = date.today()
            today_setups = self.session.query(TradeSetup).filter(
                TradeSetup.active == True,
                TradeSetup.trading_day == today
            ).count()
            
            # Find duplicate message processing
            from sqlalchemy import func
            duplicate_messages = self.session.query(
                TradeSetup.message_id,
                func.count(TradeSetup.id).label('setup_count')
            ).filter_by(active=True).group_by(TradeSetup.message_id).having(
                func.count(TradeSetup.id) > 20  # Flag messages with unusually high setup counts
            ).all()
            
            return {
                'weekend_setups': weekend_setups,
                'weekend_count': len(weekend_setups),
                'today_setups_count': today_setups,
                'duplicate_messages': [
                    {'message_id': msg_id, 'setup_count': count} 
                    for msg_id, count in duplicate_messages
                ],
                'audit_timestamp': date.today().isoformat()
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting audit anomalies: {e}")
            return {
                'weekend_setups': [],
                'weekend_count': 0,
                'today_setups_count': 0,
                'duplicate_messages': [],
                'audit_timestamp': date.today().isoformat()
            }

    def get_available_trading_days(self, limit=30):
        """Get list of trading days with setup data"""
        try:
            from sqlalchemy import distinct, func
            result = self.session.query(distinct(TradeSetup.trading_day)).filter(
                TradeSetup.trading_day.isnot(None)
            ).order_by(TradeSetup.trading_day.desc()).limit(limit).all()
            
            return [row[0] for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting available trading days: {e}")
            return []

    def get_setups_by_trading_day(self, trading_day=None):
        """Get all setups for specific trading day (default: most recent)"""
        try:
            if trading_day is None:
                # Get most recent trading day
                available_days = self.get_available_trading_days(limit=1)
                if not available_days:
                    return []
                trading_day = available_days[0]
            
            setups = self.session.query(TradeSetup).filter_by(
                trading_day=trading_day
            ).order_by(TradeSetup.created_at.desc()).all()
            
            return setups
        except SQLAlchemyError as e:
            logger.error(f"Error getting setups for trading day {trading_day}: {e}")
            return []

    def clear_all_trade_setups(self) -> Dict[str, Any]:
        """
        Clear all trade setups and their associated parsed levels.
        
        Returns:
            Dict with operation results including counts of deleted records
        """
        try:
            # Count records before deletion
            setup_count = self.session.query(TradeSetup).count()
            level_count = self.session.query(ParsedLevel).count()
            
            logger.info(f"Clearing {setup_count} trade setups and {level_count} parsed levels")
            
            # Delete parsed levels first (due to foreign key constraint)
            deleted_levels = self.session.query(ParsedLevel).delete()
            
            # Delete trade setups
            deleted_setups = self.session.query(TradeSetup).delete()
            
            # Commit the transaction
            self.session.commit()
            
            logger.info(f"Successfully cleared {deleted_setups} trade setups and {deleted_levels} parsed levels")
            
            return {
                'success': True,
                'message': 'All trade setups cleared successfully',
                'deleted_setups': deleted_setups,
                'deleted_levels': deleted_levels,
                'timestamp': datetime.now().isoformat()
            }
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error clearing trade setups: {e}")
            return {
                'success': False,
                'message': f'Failed to clear trade setups: {str(e)}',
                'deleted_setups': 0,
                'deleted_levels': 0,
                'timestamp': datetime.now().isoformat()
            }


# Global store instance
_store = None

def get_parsing_store() -> ParsingStore:
    """Get the global parsing store instance."""
    global _store
    if _store is None:
        _store = ParsingStore()
    return _store