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
from .aplus_parser import TradeSetup as ParsedTradeSetup
from .setup_converter import convert_parsed_setup_to_model, create_levels_for_setup

logger = logging.getLogger(__name__)

# Duplicate detection policy configuration
DUPLICATE_POLICY = "replace"  # Options: "skip", "replace", "allow"


# Global store instance
_parsing_store = None

def get_parsing_store() -> 'ParsingStore':
    """Get the global parsing store instance."""
    global _parsing_store
    if _parsing_store is None:
        _parsing_store = ParsingStore()
    return _parsing_store


class ParsingStore:
    """
    Store class for parsing operations.
    Handles all database interactions for trade setups and parsed levels.
    """
    
    def __init__(self):
        """Initialize the parsing store."""
        self.session = db.session
    
    def is_duplicate_setup(self, trading_day: date, message_id: str) -> bool:
        """
        Check if there's already a parsed message for this trading day.
        
        Args:
            trading_day: The trading day to check
            message_id: Current message ID to exclude from duplicate check
            
        Returns:
            True if duplicate found, False otherwise
        """
        existing = self.session.query(TradeSetup).filter_by(trading_day=trading_day).first()
        if not existing:
            return False
        if existing.message_id == message_id:
            return False  # Same message
        return True  # Conflict on trading_day
    
    def find_existing_message_for_day(self, trading_day: date) -> Optional[Tuple[str, datetime, int]]:
        """
        Find existing message for a trading day and return its details.
        
        Args:
            trading_day: The trading day to check
            
        Returns:
            Tuple of (message_id, timestamp, content_length) or None if not found
        """
        existing_setup = self.session.query(TradeSetup).filter_by(trading_day=trading_day).first()
        if not existing_setup:
            return None
        
        # Get message details from discord_messages table
        try:
            from features.ingestion.models import DiscordMessageModel
            message = self.session.query(DiscordMessageModel).filter_by(message_id=existing_setup.message_id).first()
            if not message:
                # If message not found in discord_messages, return minimal info
                return (existing_setup.message_id, existing_setup.created_at, 0)
                
            return (existing_setup.message_id, message.timestamp, len(message.content))
        except ImportError:
            # Fallback if ingestion models not available
            return (existing_setup.message_id, existing_setup.created_at, 0)
    
    def should_replace(self, existing_msg_details: Tuple[str, datetime, int], 
                      new_msg_id: str, new_timestamp: datetime, new_content_length: int) -> bool:
        """
        Determine if new message should replace existing one.
        
        Args:
            existing_msg_details: Tuple of (message_id, timestamp, content_length) for existing message
            new_msg_id: New message ID
            new_timestamp: New message timestamp
            new_content_length: New message content length
            
        Returns:
            True if new message should replace existing one
        """
        _, existing_timestamp, existing_length = existing_msg_details
        return new_timestamp > existing_timestamp and new_content_length > existing_length
    
    def delete_setups_for_trading_day(self, trading_day: date) -> int:
        """
        Delete all setups and their levels for a specific trading day.
        
        Args:
            trading_day: The trading day to clear
            
        Returns:
            Number of setups deleted
        """
        try:
            # First delete all levels for setups on this day
            setups_to_delete = self.session.query(TradeSetup).filter_by(trading_day=trading_day).all()
            levels_deleted = 0
            
            for setup in setups_to_delete:
                level_count = self.session.query(ParsedLevel).filter_by(setup_id=setup.id).count()
                self.session.query(ParsedLevel).filter_by(setup_id=setup.id).delete()
                levels_deleted += level_count
            
            # Then delete the setups
            setups_deleted = self.session.query(TradeSetup).filter_by(trading_day=trading_day).delete()
            
            logger.info(f"[store] Deleted {setups_deleted} setups and {levels_deleted} levels for trading day {trading_day}")
            return setups_deleted
            
        except SQLAlchemyError as e:
            logger.error(f"[store] Error deleting setups for trading day {trading_day}: {e}")
            self.session.rollback()
            return 0
    
    def get_duplicate_trading_days(self) -> List[Tuple[date, int]]:
        """
        Find trading days with multiple parsed messages.
        
        Returns:
            List of tuples (trading_day, message_count)
        """
        result = self.session.execute(text("""
            SELECT trading_day, COUNT(DISTINCT message_id) as msg_count
            FROM trade_setups 
            GROUP BY trading_day 
            HAVING COUNT(DISTINCT message_id) > 1
            ORDER BY trading_day DESC
        """))
        
        return [(row.trading_day, row.msg_count) for row in result]
    
    def store_parsed_message(
        self, 
        message_id: str,
        parsed_setups: List[ParsedTradeSetup], 
        trading_day: Optional[date] = None,
        ticker_bias_notes: Optional[Dict[str, str]] = None
    ) -> Tuple[List[TradeSetup], List[ParsedLevel]]:
        """
        Store parsed setups and levels from a message using the refactored TradeSetup dataclass.
        
        Args:
            message_id: Discord message ID
            parsed_setups: List of TradeSetup dataclasses from the refactored parser
            trading_day: Trading day (defaults to today)
            ticker_bias_notes: Optional dict of bias notes per ticker
            
        Returns:
            Tuple of (created_setups, created_levels)
        """
        if trading_day is None:
            trading_day = date.today()
        
        ticker_bias_notes = ticker_bias_notes or {}
        created_setups = []
        created_levels = []
        
        try:
            logger.info(f"[store] Attempting to store {len(parsed_setups)} setups for message {message_id}")
            
            for parsed_setup in parsed_setups:
                logger.info(f"[store] Processing setup: {parsed_setup.ticker} {parsed_setup.label}")
                
                # Check for existing setup to prevent duplicates
                existing = self.session.query(TradeSetup).filter_by(id=parsed_setup.id).first()
                
                if existing:
                    logger.info(f"[store] Setup {parsed_setup.id} already exists, updating...")
                    # Update existing setup
                    existing.trigger_level = parsed_setup.trigger_level
                    existing.target_prices = parsed_setup.target_prices
                    existing.direction = parsed_setup.direction
                    existing.label = parsed_setup.label
                    existing.keywords = parsed_setup.keywords
                    existing.emoji_hint = parsed_setup.emoji_hint
                    existing.raw_line = parsed_setup.raw_line
                    existing.bias_note = ticker_bias_notes.get(parsed_setup.ticker)
                    existing.updated_at = datetime.utcnow()
                    setup_model = existing
                else:
                    # Convert to database model using setup converter
                    try:
                        bias_note = ticker_bias_notes.get(parsed_setup.ticker)
                        logger.info(f"[store] Converting setup {parsed_setup.id} to database model")
                        setup_model = convert_parsed_setup_to_model(parsed_setup, message_id, bias_note)
                        logger.info(f"[store] Successfully converted setup {parsed_setup.id}")
                        self.session.add(setup_model)
                        logger.info(f"[store] Added setup {parsed_setup.id} to session")
                    except Exception as e:
                        logger.error(f"[store] Failed to convert setup {parsed_setup.id}: {e}")
                        raise
                
                try:
                    self.session.flush()  # Get the ID
                    logger.info(f"[store] Flushed setup {parsed_setup.id} to database")
                except Exception as e:
                    logger.error(f"[store] Failed to flush setup {parsed_setup.id}: {e}")
                    raise
                    
                created_setups.append(setup_model)
                
                # Create levels using converter
                try:
                    logger.info(f"[store] Creating levels for setup {parsed_setup.id}")
                    levels = create_levels_for_setup(setup_model)
                    logger.info(f"[store] Created {len(levels)} levels for setup {parsed_setup.id}")
                    
                    for level in levels:
                        # Check if level already exists
                        existing_level = self.session.query(ParsedLevel).filter_by(
                            setup_id=level.setup_id,
                            level_type=level.level_type,
                            trigger_price=level.trigger_price
                        ).first()
                        
                        if not existing_level:
                            self.session.add(level)
                            logger.debug(f"[store] Added level {level.level_type} for setup {parsed_setup.id}")
                        else:
                            logger.debug(f"[store] Level {level.level_type} already exists for setup {parsed_setup.id}")
                            
                except Exception as e:
                    logger.error(f"[store] Failed to create levels for setup {parsed_setup.id}: {e}")
                    raise
                
                created_levels.extend(levels)
                logger.debug(f"Created setup {setup_model.id} with {len(levels)} levels")
            
            # Update Discord message status to processed
            self._update_message_processed_status(message_id, True)
            
            # Commit all changes
            logger.debug(f"[store] Committing {len(created_setups)} setups and {len(created_levels)} levels to database")
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
    
    def _update_message_processed_status(self, message_id: str, is_processed: bool) -> None:
        """
        Update the is_processed status for a Discord message.
        
        Args:
            message_id: Discord message ID
            is_processed: Whether the message has been successfully processed
        """
        try:
            # Import here to avoid circular imports
            from features.ingestion.models import DiscordMessageModel
            
            message = self.session.query(DiscordMessageModel).filter_by(message_id=message_id).first()
            if message:
                message.is_processed = is_processed
                logger.debug(f"[store] Updated message {message_id} is_processed = {is_processed}")
            else:
                logger.warning(f"[store] Message {message_id} not found in discord_messages table")
                
        except Exception as e:
            logger.error(f"[store] Failed to update message processed status for {message_id}: {e}")
            # Don't raise here - this is a status update, not critical for parsing success
    
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
            # Build query conditions - use actual Discord message_id field for matching
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
        """Get comprehensive statistics about parsed data and processing effectiveness."""
        try:
            from common.timezone import get_central_trading_day
            from collections import Counter
            
            # Basic setup and level stats - using correct table names
            total_setups = self.session.query(TradeSetup).count()
            active_setups = self.session.query(TradeSetup).filter_by(active=True).count()
            total_levels = self.session.query(ParsedLevel).count()
            active_levels = self.session.query(ParsedLevel).filter_by(active=True, triggered=False).count()
            triggered_levels = self.session.query(ParsedLevel).filter_by(triggered=True).count()
            
            # Today's stats - use Central Time trading day
            today = get_central_trading_day()
            today_setups = self.session.query(TradeSetup).filter_by(trading_day=today).count()
            today_active_setups = self.session.query(TradeSetup).filter_by(
                trading_day=today, active=True
            ).count()
            
            # Enhanced metrics using new field mappings
            active_setups_query = self.session.query(TradeSetup).filter_by(active=True).all()
            
            # Metrics by setup.label
            setups_by_label = Counter(s.label for s in active_setups_query if s.label)
            
            # Metrics by setup.direction 
            direction_split = Counter(s.direction for s in active_setups_query if s.direction)
            
            # Count by setup.index (unique setups per message)
            setup_index_distribution = Counter(s.index for s in active_setups_query if s.index is not None)
            
            # Message processing effectiveness
            total_discord_messages = self.session.execute(text("SELECT COUNT(*) FROM discord_messages")).scalar()
            unique_parsed_messages = self.session.query(TradeSetup.message_id).distinct().count()
            
            # Duplicate detection
            duplicate_query = text("""
                SELECT COUNT(*) as duplicate_count
                FROM (
                    SELECT message_id, ticker, trading_day, COUNT(*) as cnt
                    FROM trade_setups 
                    GROUP BY message_id, ticker, trading_day 
                    HAVING COUNT(*) > 1
                ) as duplicates
            """)
            duplicate_count = self.session.execute(duplicate_query).scalar() or 0
            
            # Trading day distribution
            trading_day_query = text("""
                SELECT trading_day, COUNT(*) as setup_count
                FROM trade_setups 
                WHERE trading_day IS NOT NULL
                GROUP BY trading_day 
                ORDER BY trading_day DESC 
                LIMIT 10
            """)
            trading_day_distribution = [
                {'trading_day': row[0].isoformat() if row[0] else None, 'setup_count': row[1]}
                for row in self.session.execute(trading_day_query).fetchall()
            ]
            
            # Calculate processing rate
            processing_rate = (unique_parsed_messages / total_discord_messages * 100) if total_discord_messages > 0 else 0
            
            return {
                'total_setups': total_setups,
                'active_setups': active_setups,
                'total_levels': total_levels,
                'active_levels': active_levels,
                'triggered_levels': triggered_levels,
                'today_setups': today_setups,
                'today_active_setups': today_active_setups,
                'total_discord_messages': total_discord_messages,
                'unique_parsed_messages': unique_parsed_messages,
                'processing_rate': round(processing_rate, 2),
                'duplicate_count': duplicate_count,
                'trading_day_distribution': trading_day_distribution,
                # Enhanced metrics using new field mappings
                'setups_by_label': dict(setups_by_label),
                'direction_split': dict(direction_split),
                'setup_index_distribution': dict(setup_index_distribution),
                'data_quality': {
                    'messages_with_setups': unique_parsed_messages,
                    'messages_without_setups': total_discord_messages - unique_parsed_messages,
                    'has_duplicates': duplicate_count > 0,
                    'duplicate_groups': duplicate_count
                }
            }
        except Exception as e:
            logger.error(f"Error getting parsing statistics: {e}")
            return {
                'error': str(e),
                'total_setups': 0,
                'active_setups': 0,
                'processing_rate': 0
            }
    
    def cleanup_duplicate_setups(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up duplicate trade setups, keeping the first occurrence of each duplicate group.
        
        Args:
            dry_run: If True, only count duplicates without deleting
            
        Returns:
            Dict with cleanup results
        """
        try:
            # Find duplicate groups
            duplicate_query = text("""
                SELECT message_id, ticker, trading_day, COUNT(*) as duplicate_count, 
                       array_agg(id ORDER BY created_at ASC) as setup_ids
                FROM trade_setups 
                GROUP BY message_id, ticker, trading_day 
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
            """)
            
            duplicate_groups = self.session.execute(duplicate_query).fetchall()
            
            if dry_run:
                total_duplicates = sum(row[3] - 1 for row in duplicate_groups)  # -1 because we keep first one
                return {
                    'dry_run': True,
                    'duplicate_groups_found': len(duplicate_groups),
                    'total_duplicates_to_remove': total_duplicates,
                    'groups': [
                        {
                            'message_id': row[0],
                            'ticker': row[1], 
                            'trading_day': row[2].isoformat() if row[2] else None,
                            'duplicate_count': row[3],
                            'setup_ids': row[4]
                        }
                        for row in duplicate_groups
                    ]
                }
            
            # Actually remove duplicates
            removed_count = 0
            for row in duplicate_groups:
                setup_ids = row[4]
                # Keep first setup, remove the rest
                ids_to_remove = setup_ids[1:]  # Skip first ID
                
                for setup_id in ids_to_remove:
                    # First remove associated levels
                    self.session.execute(text("DELETE FROM parsing_levels WHERE setup_id = :setup_id"), 
                                       {'setup_id': setup_id})
                    # Then remove the setup
                    self.session.execute(text("DELETE FROM trade_setups WHERE id = :setup_id"), 
                                       {'setup_id': setup_id})
                    removed_count += 1
            
            self.session.commit()
            logger.info(f"Cleanup complete: removed {removed_count} duplicate setups")
            
            return {
                'dry_run': False,
                'duplicate_groups_processed': len(duplicate_groups),
                'setups_removed': removed_count,
                'success': True
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error during duplicate cleanup: {e}")
            return {
                'error': str(e),
                'success': False
            }

    def get_audit_anomalies(self) -> Dict[str, Any]:
        """Get audit data for anomalies in trade setup dates and data quality."""
        try:
            from common.timezone import get_central_trading_day
            
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
            
            # Find dates that appear to be current date (possible parsing failures) - use Central Time
            today = get_central_trading_day()
            today_setups = self.session.query(TradeSetup).filter(
                TradeSetup.active == True,
                TradeSetup.trading_day == today
            ).count()
            
            # Find duplicate message processing
            from sqlalchemy import func
            
            duplicate_messages = self.session.query(
                TradeSetup.message_id,
                func.count(TradeSetup.id).label('setup_count')
            ).group_by(TradeSetup.message_id).having(
                func.count(TradeSetup.id) > 5  # More than 5 setups per message seems unusual
            ).all()
            
            return {
                'weekend_setups': weekend_setups,
                'weekend_setup_count': len(weekend_setups),
                'today_setup_count': today_setups,
                'duplicate_messages': [
                    {'message_id': msg[0], 'setup_count': msg[1]} 
                    for msg in duplicate_messages
                ],
                'audit_timestamp': datetime.utcnow(),
                'anomaly_summary': {
                    'has_weekend_trading': len(weekend_setups) > 0,
                    'has_suspicious_volume': len(duplicate_messages) > 0,
                    'today_is_trading_day': today.weekday() < 5  # Monday=0 to Friday=4
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting audit anomalies: {e}")
            return {
                'error': str(e),
                'weekend_setups': [],
                'weekend_setup_count': 0,
                'today_setup_count': 0,
                'duplicate_messages': [],
                'audit_timestamp': datetime.utcnow()
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