"""
Parsing Audit Module

Comprehensive audit functionality to track parsing completeness,
message-to-setup conversion rates, and identify parsing issues.
"""
import logging
from datetime import date
from typing import Dict, Any, List, Tuple
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

from .models import TradeSetup, ParsedLevel
from features.ingestion.models import DiscordMessageModel
from common.database import get_database_manager

logger = logging.getLogger(__name__)


class ParsingAudit:
    """Audit class for parsing completeness and data quality analysis."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    def get_message_coverage_audit(self) -> Dict[str, Any]:
        """
        Audit A: Setup Coverage vs Message Count
        Compare total messages ingested vs messages that led to setups.
        """
        try:
            with self.db_manager.get_session() as session:
                # Total messages ingested
                total_messages = session.query(DiscordMessageModel).count()
                
                # Messages that led to setups
                messages_with_setups = session.query(func.count(func.distinct(TradeSetup.message_id))).scalar()
                
                # Coverage percentage
                coverage_rate = round((messages_with_setups / total_messages * 100), 2) if total_messages > 0 else 0
                
                return {
                    'total_messages_ingested': total_messages,
                    'messages_with_setups': messages_with_setups,
                    'messages_without_setups': total_messages - messages_with_setups,
                    'coverage_rate_percent': coverage_rate,
                    'audit_type': 'message_coverage'
                }
        except SQLAlchemyError as e:
            logger.error(f"Error in message coverage audit: {e}")
            return {'error': str(e), 'audit_type': 'message_coverage'}
    
    def get_setups_per_trading_day_audit(self) -> Dict[str, Any]:
        """
        Audit B: Setups per Trading Day
        Analyze setup distribution across trading days.
        """
        try:
            with self.db_manager.get_session() as session:
                # Group setups by trading day
                trading_day_stats = session.query(
                    TradeSetup.trading_day,
                    func.count(TradeSetup.id).label('setup_count'),
                    func.count(func.distinct(TradeSetup.message_id)).label('message_count')
                ).filter(
                    TradeSetup.active == True
                ).group_by(
                    TradeSetup.trading_day
                ).order_by(
                    TradeSetup.trading_day.desc()
                ).all()
                
                # Convert to list of dictionaries
                daily_stats = []
                for trading_day, setup_count, message_count in trading_day_stats:
                    daily_stats.append({
                        'trading_day': trading_day.isoformat() if trading_day else None,
                        'setup_count': setup_count,
                        'message_count': message_count,
                        'setups_per_message': round(setup_count / message_count, 2) if message_count > 0 else 0
                    })
                
                return {
                    'daily_statistics': daily_stats,
                    'unique_trading_days': len(daily_stats),
                    'audit_type': 'setups_per_trading_day'
                }
        except SQLAlchemyError as e:
            logger.error(f"Error in setups per trading day audit: {e}")
            return {'error': str(e), 'audit_type': 'setups_per_trading_day'}
    
    def get_missing_trading_day_audit(self) -> Dict[str, Any]:
        """
        Audit C: Setups Missing Trading Day
        Identify setups with null trading_day values.
        """
        try:
            with self.db_manager.get_session() as session:
                # Count setups with null trading_day
                missing_trading_day_count = session.query(TradeSetup).filter(
                    TradeSetup.trading_day.is_(None)
                ).count()
                
                # Get sample records for investigation
                sample_records = session.query(TradeSetup).filter(
                    TradeSetup.trading_day.is_(None)
                ).limit(10).all()
                
                sample_data = []
                for setup in sample_records:
                    sample_data.append({
                        'id': setup.id,
                        'message_id': setup.message_id,
                        'ticker': setup.ticker,
                        'created_at': setup.created_at.isoformat() if setup.created_at else None,
                        'raw_content': setup.raw_content[:100] if setup.raw_content else None
                    })
                
                return {
                    'missing_trading_day_count': missing_trading_day_count,
                    'sample_records': sample_data,
                    'audit_type': 'missing_trading_day'
                }
        except SQLAlchemyError as e:
            logger.error(f"Error in missing trading day audit: {e}")
            return {'error': str(e), 'audit_type': 'missing_trading_day'}
    
    def get_message_parsing_completeness_audit(self) -> Dict[str, Any]:
        """
        Audit D: Messages Without Associated Setups
        Find messages in discord_messages that have no corresponding trade_setups.
        """
        try:
            with self.db_manager.get_session() as session:
                # Messages without setups using left join
                query = session.query(DiscordMessage).outerjoin(
                    TradeSetup, DiscordMessage.message_id == TradeSetup.message_id
                ).filter(TradeSetup.message_id.is_(None))
                
                orphaned_messages = query.limit(20).all()
                orphaned_count = query.count()
                
                orphaned_data = []
                for msg in orphaned_messages:
                    orphaned_data.append({
                        'message_id': msg.message_id,
                        'channel_id': msg.channel_id,
                        'content_preview': msg.content[:100] if msg.content else None,
                        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                        'processed': msg.processed
                    })
                
                return {
                    'orphaned_messages_count': orphaned_count,
                    'sample_orphaned_messages': orphaned_data,
                    'audit_type': 'message_parsing_completeness'
                }
        except SQLAlchemyError as e:
            logger.error(f"Error in message parsing completeness audit: {e}")
            return {'error': str(e), 'audit_type': 'message_parsing_completeness'}
    
    def get_duplicate_setups_audit(self) -> Dict[str, Any]:
        """
        Audit E: Duplicate Setups Analysis
        Find potential duplicate setups based on message_id + ticker + trading_day.
        """
        try:
            with self.db_manager.get_session() as session:
                # Find potential duplicates
                duplicates_query = session.query(
                    TradeSetup.message_id,
                    TradeSetup.ticker,
                    TradeSetup.trading_day,
                    func.count(TradeSetup.id).label('duplicate_count')
                ).group_by(
                    TradeSetup.message_id,
                    TradeSetup.ticker,
                    TradeSetup.trading_day
                ).having(
                    func.count(TradeSetup.id) > 1
                ).all()
                
                duplicate_groups = []
                for msg_id, ticker, trading_day, count in duplicates_query:
                    duplicate_groups.append({
                        'message_id': msg_id,
                        'ticker': ticker,
                        'trading_day': trading_day.isoformat() if trading_day else None,
                        'duplicate_count': count
                    })
                
                return {
                    'duplicate_groups_found': len(duplicate_groups),
                    'duplicate_groups': duplicate_groups,
                    'audit_type': 'duplicate_setups'
                }
        except SQLAlchemyError as e:
            logger.error(f"Error in duplicate setups audit: {e}")
            return {'error': str(e), 'audit_type': 'duplicate_setups'}
    
    def get_comprehensive_audit_report(self) -> Dict[str, Any]:
        """Get all audit results in a comprehensive report."""
        return {
            'message_coverage': self.get_message_coverage_audit(),
            'setups_per_trading_day': self.get_setups_per_trading_day_audit(),
            'missing_trading_day': self.get_missing_trading_day_audit(),
            'message_parsing_completeness': self.get_message_parsing_completeness_audit(),
            'duplicate_setups': self.get_duplicate_setups_audit(),
            'audit_timestamp': date.today().isoformat()
        }


# Global audit instance
_audit = None

def get_parsing_audit() -> ParsingAudit:
    """Get the global parsing audit instance."""
    global _audit
    if _audit is None:
        _audit = ParsingAudit()
    return _audit