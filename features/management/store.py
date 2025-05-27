"""
Management Store Module

Database access layer for managing trading setups and related data.
Migrated from legacy setups/repository.py with enhanced query patterns.
"""
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError

from common.db import db, publish_event
from features.parsing.models import SetupModel
from common.event_constants import EventChannels

logger = logging.getLogger(__name__)


class SetupStore:
    """
    Data access layer for trading setup management.
    
    Provides methods for storing, retrieving, and managing trading setups
    with proper transaction boundaries and error handling.
    """
    
    def store_setup(self, setup_data: Dict[str, Any]) -> bool:
        """
        Store setup data in database with proper error handling.
        
        Args:
            setup_data: Dictionary containing setup information
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            setup = SetupModel(
                ticker=setup_data.get('ticker'),
                content=setup_data.get('content', ''),
                message_id=setup_data.get('message_id'),
                date=setup_data.get('date', date.today()),
                setup_type=setup_data.get('setup_type', 'unknown'),
                direction=setup_data.get('direction'),
                price_level=setup_data.get('price_level'),
                confidence=setup_data.get('confidence', 0.0),
                source=setup_data.get('source', 'discord'),
                active=setup_data.get('active', True),
                parsed_at=datetime.utcnow()
            )
            
            db.session.add(setup)
            db.session.commit()
            
            # Publish setup creation event
            publish_event(EventChannels.SETUP_CREATED, {
                'setup_id': setup.id,
                'ticker': setup.ticker,
                'setup_type': setup.setup_type,
                'source': setup.source
            })
            
            logger.info(f"Successfully stored setup for {setup.ticker}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error storing setup: {e}")
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing setup data: {e}")
            return False
    
    def get_recent_setups(self, limit: int = 100) -> List[SetupModel]:
        """
        Get recent setups from database ordered by creation time.
        
        Args:
            limit: Maximum number of setups to retrieve
            
        Returns:
            List of SetupModel instances
        """
        try:
            setups = SetupModel.query.order_by(
                desc(SetupModel.parsed_at)
            ).limit(limit).all()
            
            logger.debug(f"Retrieved {len(setups)} recent setups")
            return setups
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving recent setups: {e}")
            return []
    
    def get_setups_by_ticker(self, ticker: str, limit: int = 50) -> List[SetupModel]:
        """
        Get setups for a specific ticker symbol.
        
        Args:
            ticker: The ticker symbol to search for
            limit: Maximum number of setups to retrieve
            
        Returns:
            List of SetupModel instances for the ticker
        """
        try:
            setups = SetupModel.query.filter(
                SetupModel.ticker == ticker.upper()
            ).order_by(
                desc(SetupModel.parsed_at)
            ).limit(limit).all()
            
            logger.debug(f"Retrieved {len(setups)} setups for {ticker}")
            return setups
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving setups for {ticker}: {e}")
            return []
    
    def get_active_setups(self) -> List[SetupModel]:
        """
        Get all active setups (not executed or cancelled).
        
        Returns:
            List of active SetupModel instances
        """
        try:
            setups = SetupModel.query.filter(
                SetupModel.active == True
            ).order_by(
                desc(SetupModel.parsed_at)
            ).all()
            
            logger.debug(f"Retrieved {len(setups)} active setups")
            return setups
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving active setups: {e}")
            return []
    
    def get_setups_by_date(self, target_date: date) -> List[SetupModel]:
        """
        Get setups for a specific date.
        
        Args:
            target_date: The date to search for
            
        Returns:
            List of SetupModel instances for the date
        """
        try:
            setups = SetupModel.query.filter(
                SetupModel.date == target_date
            ).order_by(
                desc(SetupModel.parsed_at)
            ).all()
            
            logger.debug(f"Retrieved {len(setups)} setups for {target_date}")
            return setups
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving setups for {target_date}: {e}")
            return []
    
    def update_setup_status(self, setup_id: int, active: bool) -> bool:
        """
        Update the active status of a setup.
        
        Args:
            setup_id: ID of the setup to update
            active: New active status
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            setup = SetupModel.query.get(setup_id)
            if not setup:
                logger.warning(f"Setup {setup_id} not found")
                return False
            
            setup.active = active
            db.session.commit()
            
            # Publish setup update event
            publish_event(EventChannels.SETUP_UPDATED, {
                'setup_id': setup_id,
                'ticker': setup.ticker,
                'active': active
            })
            
            logger.info(f"Updated setup {setup_id} active status to {active}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating setup {setup_id}: {e}")
            return False
    
    def get_setup_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored setups.
        
        Returns:
            Dictionary containing setup statistics
        """
        try:
            total_setups = SetupModel.query.count()
            active_setups = SetupModel.query.filter(SetupModel.active == True).count()
            
            # Get setup counts by ticker
            ticker_counts = db.session.query(
                SetupModel.ticker,
                func.count(SetupModel.id).label('count')
            ).group_by(SetupModel.ticker).order_by(
                desc(func.count(SetupModel.id))
            ).limit(10).all()
            
            # Get recent activity (last 7 days)
            recent_date = datetime.utcnow().date()
            recent_count = SetupModel.query.filter(
                SetupModel.date >= recent_date
            ).count()
            
            stats = {
                'total_setups': total_setups,
                'active_setups': active_setups,
                'recent_setups': recent_count,
                'top_tickers': [{'ticker': t[0], 'count': t[1]} for t in ticker_counts]
            }
            
            logger.debug(f"Generated setup statistics: {stats}")
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Database error generating statistics: {e}")
            return {
                'total_setups': 0,
                'active_setups': 0,
                'recent_setups': 0,
                'top_tickers': []
            }
    
    def search_setups(self, search_term: str, limit: int = 50) -> List[SetupModel]:
        """
        Search setups by content or ticker.
        
        Args:
            search_term: Term to search for
            limit: Maximum number of results
            
        Returns:
            List of matching SetupModel instances
        """
        try:
            setups = SetupModel.query.filter(
                db.or_(
                    SetupModel.ticker.ilike(f'%{search_term}%'),
                    SetupModel.content.ilike(f'%{search_term}%')
                )
            ).order_by(
                desc(SetupModel.parsed_at)
            ).limit(limit).all()
            
            logger.debug(f"Search for '{search_term}' returned {len(setups)} results")
            return setups
            
        except SQLAlchemyError as e:
            logger.error(f"Database error searching setups: {e}")
            return []


# Global store instance
setup_store = SetupStore()


def get_setup_store() -> SetupStore:
    """
    Get the global setup store instance.
    
    Returns:
        SetupStore: The global store instance
    """
    return setup_store